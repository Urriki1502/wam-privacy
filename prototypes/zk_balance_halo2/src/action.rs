//! Phase 9-A: integrated anchored-spend action relation.
//!
//! This circuit closes the Phase 8C/8D composition gap by assigning one
//! private note_identity cell and using that same constrained cell for:
//!
//! 1. commitment-tree membership against a public anchor;
//! 2. spend-authority tagging; and
//! 3. note-bound nullifier derivation.
//!
//! Public instances:
//! - row 0: commitment-tree root;
//! - row 1: authority tag;
//! - row 2: nullifier.
//!
//! This remains an isolated research relation. note_identity is still a
//! circuit-native field encoding, not yet a full production note commitment.

use halo2_gadgets::poseidon::{
    primitives::{ConstantLength, Hash as PrimitiveHash, P128Pow5T3},
    Hash as PoseidonHash, Pow5Chip, Pow5Config,
};
use halo2_proofs::{
    circuit::{AssignedCell, Layouter, SimpleFloorPlanner, Value},
    pasta::Fp,
    plonk::{
        Advice, Circuit, Column, ConstraintSystem, Error, Expression, Fixed, Instance, Selector,
    },
    poly::Rotation,
};

use crate::{
    anchor::TREE_DEPTH,
    nullifier::{AUTHORITY_DOMAIN, NULLIFIER_DOMAIN},
};

const WIDTH: usize = 3;
const RATE: usize = 2;
const HASH_INPUTS: usize = 2;

#[derive(Clone, Debug)]
pub struct ActionConfig {
    witness: Column<Advice>,
    sibling: Column<Advice>,
    direction: Column<Advice>,
    left: Column<Advice>,
    right: Column<Advice>,
    select: Selector,
    instance: Column<Instance>,
    poseidon: Pow5Config<Fp, WIDTH, RATE>,
}

#[derive(Clone, Debug)]
pub struct ActionCircuit {
    pub spend_secret: Fp,
    pub note_identity: Fp,
    pub siblings: [Fp; TREE_DEPTH],
    pub directions: [bool; TREE_DEPTH],
}

impl Default for ActionCircuit {
    fn default() -> Self {
        Self {
            spend_secret: Fp::zero(),
            note_identity: Fp::zero(),
            siblings: [Fp::zero(); TREE_DEPTH],
            directions: [false; TREE_DEPTH],
        }
    }
}

pub fn poseidon_pair(left: Fp, right: Fp) -> Fp {
    PrimitiveHash::<Fp, P128Pow5T3, ConstantLength<HASH_INPUTS>, WIDTH, RATE>::init()
        .hash([left, right])
}

pub fn authority_tag(spend_secret: Fp) -> Fp {
    poseidon_pair(Fp::from(AUTHORITY_DOMAIN), spend_secret)
}

pub fn nullifier(spend_secret: Fp, note_identity: Fp) -> Fp {
    let note_key = poseidon_pair(spend_secret, note_identity);
    poseidon_pair(Fp::from(NULLIFIER_DOMAIN), note_key)
}

pub fn merkle_root(
    mut current: Fp,
    siblings: [Fp; TREE_DEPTH],
    directions: [bool; TREE_DEPTH],
) -> Fp {
    for (sibling, is_right) in siblings.into_iter().zip(directions) {
        current = if is_right {
            poseidon_pair(sibling, current)
        } else {
            poseidon_pair(current, sibling)
        };
    }
    current
}

impl ActionCircuit {
    pub fn public_inputs(&self) -> Vec<Fp> {
        vec![
            merkle_root(self.note_identity, self.siblings, self.directions),
            authority_tag(self.spend_secret),
            nullifier(self.spend_secret, self.note_identity),
        ]
    }
}

fn hash_cells(
    config: &ActionConfig,
    layouter: &mut impl Layouter<Fp>,
    left: AssignedCell<Fp, Fp>,
    right: AssignedCell<Fp, Fp>,
    label: &str,
) -> Result<AssignedCell<Fp, Fp>, Error> {
    let chip = Pow5Chip::construct(config.poseidon.clone());
    PoseidonHash::<
        Fp,
        Pow5Chip<Fp, WIDTH, RATE>,
        P128Pow5T3,
        ConstantLength<HASH_INPUTS>,
        WIDTH,
        RATE,
    >::init(chip, layouter.namespace(|| format!("{label} init")))?
    .hash(
        layouter.namespace(|| format!("{label} hash")),
        [left, right],
    )
}

impl Circuit<Fp> for ActionCircuit {
    type Config = ActionConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let witness = meta.advice_column();
        let sibling = meta.advice_column();
        let direction = meta.advice_column();
        let left = meta.advice_column();
        let right = meta.advice_column();
        let instance = meta.instance_column();

        for column in [witness, sibling, direction, left, right] {
            meta.enable_equality(column);
        }
        meta.enable_equality(instance);

        let select = meta.selector();

        meta.create_gate("integrated merkle child ordering", |meta| {
            let s = meta.query_selector(select);
            let current = meta.query_advice(witness, Rotation::cur());
            let sibling_v = meta.query_advice(sibling, Rotation::cur());
            let bit = meta.query_advice(direction, Rotation::cur());
            let left_v = meta.query_advice(left, Rotation::cur());
            let right_v = meta.query_advice(right, Rotation::cur());
            let one = Expression::Constant(Fp::one());

            vec![
                s.clone() * bit.clone() * (bit.clone() - one),
                s.clone()
                    * (left_v
                        - (current.clone() + bit.clone() * (sibling_v.clone() - current.clone()))),
                s * (right_v - (sibling_v.clone() + bit * (current - sibling_v))),
            ]
        });

        let state = [
            meta.advice_column(),
            meta.advice_column(),
            meta.advice_column(),
        ];
        let partial_sbox = meta.advice_column();
        let rc_a: [Column<Fixed>; WIDTH] = [
            meta.fixed_column(),
            meta.fixed_column(),
            meta.fixed_column(),
        ];
        let rc_b: [Column<Fixed>; WIDTH] = [
            meta.fixed_column(),
            meta.fixed_column(),
            meta.fixed_column(),
        ];
        let constants = meta.fixed_column();
        meta.enable_constant(constants);

        let poseidon = Pow5Chip::configure::<P128Pow5T3>(meta, state, partial_sbox, rc_a, rc_b);

        ActionConfig {
            witness,
            sibling,
            direction,
            left,
            right,
            select,
            instance,
            poseidon,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        let (note_identity, spend_secret, authority_domain, nullifier_domain) = layouter
            .assign_region(
                || "load integrated action witnesses",
                |mut region| {
                    let note_identity = region.assign_advice(
                        || "private note identity",
                        config.witness,
                        0,
                        || Value::known(self.note_identity),
                    )?;
                    let spend_secret = region.assign_advice(
                        || "private spend authority",
                        config.witness,
                        1,
                        || Value::known(self.spend_secret),
                    )?;
                    let authority_domain = region.assign_advice_from_constant(
                        || "authority domain",
                        config.witness,
                        2,
                        Fp::from(AUTHORITY_DOMAIN),
                    )?;
                    let nullifier_domain = region.assign_advice_from_constant(
                        || "nullifier domain",
                        config.witness,
                        3,
                        Fp::from(NULLIFIER_DOMAIN),
                    )?;

                    Ok((
                        note_identity,
                        spend_secret,
                        authority_domain,
                        nullifier_domain,
                    ))
                },
            )?;

        // Membership branch: the exact same note_identity cell becomes the
        // Merkle leaf. This is the critical Phase 9 composition constraint.
        let mut current = note_identity.clone();
        let mut current_value = self.note_identity;

        for level in 0..TREE_DEPTH {
            let sibling_value = self.siblings[level];
            let direction_value = self.directions[level];

            let (left_cell, right_cell) = layouter.assign_region(
                || format!("integrated anchor path level {level}"),
                |mut region| {
                    config.select.enable(&mut region, 0)?;

                    current.copy_advice(|| "current node", &mut region, config.witness, 0)?;
                    region.assign_advice(
                        || "sibling node",
                        config.sibling,
                        0,
                        || Value::known(sibling_value),
                    )?;
                    region.assign_advice(
                        || "direction bit",
                        config.direction,
                        0,
                        || Value::known(Fp::from(direction_value as u64)),
                    )?;

                    let left_value = if direction_value {
                        sibling_value
                    } else {
                        current_value
                    };
                    let right_value = if direction_value {
                        current_value
                    } else {
                        sibling_value
                    };

                    let left_cell = region.assign_advice(
                        || "ordered left child",
                        config.left,
                        0,
                        || Value::known(left_value),
                    )?;
                    let right_cell = region.assign_advice(
                        || "ordered right child",
                        config.right,
                        0,
                        || Value::known(right_value),
                    )?;

                    Ok((left_cell, right_cell))
                },
            )?;

            current = hash_cells(
                &config,
                &mut layouter,
                left_cell,
                right_cell,
                &format!("integrated anchor parent {level}"),
            )?;

            current_value = if direction_value {
                poseidon_pair(sibling_value, current_value)
            } else {
                poseidon_pair(current_value, sibling_value)
            };
        }

        layouter.constrain_instance(current.cell(), config.instance, 0)?;

        // Spend-authority branch.
        let tag = hash_cells(
            &config,
            &mut layouter,
            authority_domain,
            spend_secret.clone(),
            "integrated authority tag",
        )?;
        layouter.constrain_instance(tag.cell(), config.instance, 1)?;

        // Nullifier branch uses the original note_identity cell, not a second
        // unconstrained witness.
        let note_key = hash_cells(
            &config,
            &mut layouter,
            spend_secret,
            note_identity,
            "integrated note-bound secret",
        )?;
        let nf = hash_cells(
            &config,
            &mut layouter,
            nullifier_domain,
            note_key,
            "integrated nullifier",
        )?;
        layouter.constrain_instance(nf.cell(), config.instance, 2)
    }
}
