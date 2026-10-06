//! Phase 8-C: commitment-tree anchor membership prototype.
//!
//! This module constrains a private Merkle authentication path to a public
//! root using the standard Poseidon gadget shipped with Zcash Halo2.
//!
//! Scope:
//! - the leaf is already a field-encoded note commitment;
//! - siblings and direction bits are private witnesses;
//! - the final anchor is a public instance;
//! - every direction bit is boolean-constrained;
//! - each parent is Poseidon(left, right).
//!
//! This does NOT yet derive the note commitment from private note fields and
//! does not claim compatibility with the Phase 7 SHA-256 placeholder root.
//! It proves the tree-membership relation for the Phase 8 circuit-native tree.

use halo2_gadgets::poseidon::{
    primitives::{ConstantLength, Hash as PrimitiveHash, P128Pow5T3},
    Hash as PoseidonHash, Pow5Chip, Pow5Config,
};
use halo2_proofs::{
    circuit::{AssignedCell, Layouter, SimpleFloorPlanner, Value},
    pasta::Fp,
    plonk::{Advice, Circuit, Column, ConstraintSystem, Error, Fixed, Instance, Selector},
    poly::Rotation,
};

pub const TREE_DEPTH: usize = 4;
const WIDTH: usize = 3;
const RATE: usize = 2;
const HASH_INPUTS: usize = 2;

#[derive(Clone, Debug)]
pub struct AnchorConfig {
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
pub struct AnchorCircuit {
    pub leaf: Fp,
    pub siblings: [Fp; TREE_DEPTH],
    pub directions: [bool; TREE_DEPTH],
}

impl Default for AnchorCircuit {
    fn default() -> Self {
        Self {
            leaf: Fp::zero(),
            siblings: [Fp::zero(); TREE_DEPTH],
            directions: [false; TREE_DEPTH],
        }
    }
}

impl AnchorCircuit {
    pub fn root(&self) -> Fp {
        merkle_root(self.leaf, self.siblings, self.directions)
    }
}

pub fn poseidon_pair(left: Fp, right: Fp) -> Fp {
    PrimitiveHash::<Fp, P128Pow5T3, ConstantLength<HASH_INPUTS>, WIDTH, RATE>::init()
        .hash([left, right])
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

impl Circuit<Fp> for AnchorCircuit {
    type Config = AnchorConfig;
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

        meta.create_gate("merkle child ordering", |meta| {
            let s = meta.query_selector(select);
            let current = meta.query_advice(witness, Rotation::cur());
            let sibling_v = meta.query_advice(sibling, Rotation::cur());
            let bit = meta.query_advice(direction, Rotation::cur());
            let left_v = meta.query_advice(left, Rotation::cur());
            let right_v = meta.query_advice(right, Rotation::cur());
            let one = halo2_proofs::plonk::Expression::Constant(Fp::one());

            vec![
                s.clone() * bit.clone() * (bit.clone() - one),
                s.clone()
                    * (left_v
                        - (current.clone()
                            + bit.clone() * (sibling_v.clone() - current.clone()))),
                s * (right_v
                    - (sibling_v.clone() + bit * (current - sibling_v))),
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
        let poseidon =
            Pow5Chip::configure::<P128Pow5T3>(meta, state, partial_sbox, rc_a, rc_b);

        AnchorConfig {
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
        let mut current = layouter.assign_region(
            || "load anchor leaf",
            |mut region| {
                region.assign_advice(
                    || "private note commitment leaf",
                    config.witness,
                    0,
                    || Value::known(self.leaf),
                )
            },
        )?;

        let mut current_value = self.leaf;

        for level in 0..TREE_DEPTH {
            let sibling_value = self.siblings[level];
            let direction_value = self.directions[level];

            let (left_cell, right_cell) = layouter.assign_region(
                || format!("anchor path level {level}"),
                |mut region| {
                    config.select.enable(&mut region, 0)?;

                    let current_copy =
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

                    // Keep the copied current cell live in the region and constrain
                    // ordering through the gate above.
                    let _ = current_copy;

                    Ok((left_cell, right_cell))
                },
            )?;

            let poseidon = Pow5Chip::construct(config.poseidon.clone());
            current = PoseidonHash::<
                Fp,
                Pow5Chip<Fp, WIDTH, RATE>,
                P128Pow5T3,
                ConstantLength<HASH_INPUTS>,
                WIDTH,
                RATE,
            >::init(poseidon, layouter.namespace(|| format!("poseidon init {level}")))?
            .hash(
                layouter.namespace(|| format!("poseidon parent {level}")),
                [left_cell, right_cell],
            )?;

            current_value = if direction_value {
                poseidon_pair(sibling_value, current_value)
            } else {
                poseidon_pair(current_value, sibling_value)
            };
        }

        layouter.constrain_instance(current.cell(), config.instance, 0)
    }
}
