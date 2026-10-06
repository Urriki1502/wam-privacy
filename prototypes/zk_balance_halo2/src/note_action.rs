//! Phase 9-B: integrated note-field commitment + anchored-spend action.
//!
//! Phase 9A accepted a pre-computed circuit-native note_identity witness.
//! Phase 9B removes that boundary. The note identity is derived in-circuit
//! from private note fields and the resulting cell is used directly as:
//!
//! - the commitment-tree leaf; and
//! - the note input to nullifier derivation.
//!
//! Private note fields:
//! - value;
//! - recipient_tag;
//! - spend_secret (represented through its authority tag in the note);
//! - rho;
//! - rseed.
//!
//! Public instances:
//! - row 0: commitment-tree root;
//! - row 1: authority tag;
//! - row 2: nullifier.
//!
//! This is a circuit-native research encoding, not a final WAM note format.

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
    MAX_WAM_ATOMS,
};

const WIDTH: usize = 3;
const RATE: usize = 2;
const HASH_INPUTS: usize = 2;
const RANGE_BITS: usize = 64;

/// Circuit-native note commitment domain. This is deliberately not presented
/// as a consensus encoding.
pub const NOTE_DOMAIN: u64 = 0x5741_4d43; // "WAMC"

#[derive(Clone, Debug)]
pub struct NoteActionConfig {
    witness: Column<Advice>,
    note_value: Column<Advice>,
    cap_slack: Column<Advice>,
    value_minus_one: Column<Advice>,
    range_acc: Column<Advice>,
    range_bit: Column<Advice>,
    sibling: Column<Advice>,
    direction: Column<Advice>,
    left: Column<Advice>,
    right: Column<Advice>,
    path_select: Selector,
    cap_select: Selector,
    positive_select: Selector,
    range_select: Selector,
    range_final_select: Selector,
    instance: Column<Instance>,
    poseidon: Pow5Config<Fp, WIDTH, RATE>,
}

#[derive(Clone, Debug)]
pub struct NoteActionCircuit {
    pub value: u64,
    pub recipient_tag: Fp,
    pub spend_secret: Fp,
    pub rho: Fp,
    pub rseed: Fp,
    pub siblings: [Fp; TREE_DEPTH],
    pub directions: [bool; TREE_DEPTH],
}

impl Default for NoteActionCircuit {
    fn default() -> Self {
        Self {
            value: 1,
            recipient_tag: Fp::zero(),
            spend_secret: Fp::zero(),
            rho: Fp::zero(),
            rseed: Fp::zero(),
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

pub fn note_identity(
    value: u64,
    recipient_tag: Fp,
    spend_authority_tag: Fp,
    rho: Fp,
    rseed: Fp,
) -> Fp {
    let h0 = poseidon_pair(Fp::from(NOTE_DOMAIN), Fp::from(value));
    let h1 = poseidon_pair(h0, recipient_tag);
    let h2 = poseidon_pair(h1, spend_authority_tag);
    let h3 = poseidon_pair(h2, rho);
    poseidon_pair(h3, rseed)
}

pub fn nullifier(spend_secret: Fp, identity: Fp) -> Fp {
    let note_key = poseidon_pair(spend_secret, identity);
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

impl NoteActionCircuit {
    pub fn native_note_identity(&self) -> Fp {
        let tag = authority_tag(self.spend_secret);
        note_identity(self.value, self.recipient_tag, tag, self.rho, self.rseed)
    }

    pub fn public_inputs(&self) -> Vec<Fp> {
        let tag = authority_tag(self.spend_secret);
        let identity = note_identity(self.value, self.recipient_tag, tag, self.rho, self.rseed);
        vec![
            merkle_root(identity, self.siblings, self.directions),
            tag,
            nullifier(self.spend_secret, identity),
        ]
    }
}

fn hash_cells(
    config: &NoteActionConfig,
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

impl Circuit<Fp> for NoteActionCircuit {
    type Config = NoteActionConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let witness = meta.advice_column();
        let note_value = meta.advice_column();
        let cap_slack = meta.advice_column();
        let value_minus_one = meta.advice_column();
        let range_acc = meta.advice_column();
        let range_bit = meta.advice_column();
        let sibling = meta.advice_column();
        let direction = meta.advice_column();
        let left = meta.advice_column();
        let right = meta.advice_column();
        let instance = meta.instance_column();

        for column in [
            witness,
            note_value,
            cap_slack,
            value_minus_one,
            range_acc,
            sibling,
            direction,
            left,
            right,
        ] {
            meta.enable_equality(column);
        }
        meta.enable_equality(instance);

        let path_select = meta.selector();
        let cap_select = meta.selector();
        let positive_select = meta.selector();
        let range_select = meta.selector();
        let range_final_select = meta.selector();

        meta.create_gate("phase9b note value cap", |meta| {
            let s = meta.query_selector(cap_select);
            let value = meta.query_advice(note_value, Rotation::cur());
            let slack = meta.query_advice(cap_slack, Rotation::cur());
            let cap = Expression::Constant(Fp::from(MAX_WAM_ATOMS));
            vec![s * (value + slack - cap)]
        });

        meta.create_gate("phase9b nonzero note value", |meta| {
            let s = meta.query_selector(positive_select);
            let value = meta.query_advice(note_value, Rotation::cur());
            let prior = meta.query_advice(value_minus_one, Rotation::cur());
            vec![s * (value - prior - Expression::Constant(Fp::one()))]
        });

        meta.create_gate("phase9b 64-bit decomposition", |meta| {
            let s = meta.query_selector(range_select);
            let acc = meta.query_advice(range_acc, Rotation::cur());
            let next = meta.query_advice(range_acc, Rotation::next());
            let bit = meta.query_advice(range_bit, Rotation::cur());
            let one = Expression::Constant(Fp::one());
            let two = Expression::Constant(Fp::from(2));

            vec![
                s.clone() * (acc - bit.clone() - two * next),
                s * bit.clone() * (bit - one),
            ]
        });

        meta.create_gate("phase9b range termination", |meta| {
            let s = meta.query_selector(range_final_select);
            let acc = meta.query_advice(range_acc, Rotation::cur());
            vec![s * acc]
        });

        meta.create_gate("phase9b merkle child ordering", |meta| {
            let s = meta.query_selector(path_select);
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

        NoteActionConfig {
            witness,
            note_value,
            cap_slack,
            value_minus_one,
            range_acc,
            range_bit,
            sibling,
            direction,
            left,
            right,
            path_select,
            cap_select,
            positive_select,
            range_select,
            range_final_select,
            instance,
            poseidon,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        let slack_value = MAX_WAM_ATOMS.saturating_sub(self.value);
        let prior_value = self.value.saturating_sub(1);

        let (
            value_cell,
            slack_cell,
            prior_cell,
            recipient,
            spend_secret,
            rho,
            rseed,
            note_domain,
            authority_domain,
            nullifier_domain,
        ) = layouter.assign_region(
            || "load phase9b private note fields",
            |mut region| {
                config.cap_select.enable(&mut region, 0)?;
                config.positive_select.enable(&mut region, 0)?;

                let value_cell = region.assign_advice(
                    || "private note value",
                    config.note_value,
                    0,
                    || Value::known(Fp::from(self.value)),
                )?;
                let slack_cell = region.assign_advice(
                    || "monetary cap slack",
                    config.cap_slack,
                    0,
                    || Value::known(Fp::from(slack_value)),
                )?;
                let prior_cell = region.assign_advice(
                    || "value minus one",
                    config.value_minus_one,
                    0,
                    || Value::known(Fp::from(prior_value)),
                )?;

                let recipient = region.assign_advice(
                    || "private recipient tag",
                    config.witness,
                    1,
                    || Value::known(self.recipient_tag),
                )?;
                let spend_secret = region.assign_advice(
                    || "private spend secret",
                    config.witness,
                    2,
                    || Value::known(self.spend_secret),
                )?;
                let rho = region.assign_advice(
                    || "private rho",
                    config.witness,
                    3,
                    || Value::known(self.rho),
                )?;
                let rseed = region.assign_advice(
                    || "private rseed",
                    config.witness,
                    4,
                    || Value::known(self.rseed),
                )?;

                let note_domain = region.assign_advice_from_constant(
                    || "note domain",
                    config.witness,
                    5,
                    Fp::from(NOTE_DOMAIN),
                )?;
                let authority_domain = region.assign_advice_from_constant(
                    || "authority domain",
                    config.witness,
                    6,
                    Fp::from(AUTHORITY_DOMAIN),
                )?;
                let nullifier_domain = region.assign_advice_from_constant(
                    || "nullifier domain",
                    config.witness,
                    7,
                    Fp::from(NULLIFIER_DOMAIN),
                )?;

                Ok((
                    value_cell,
                    slack_cell,
                    prior_cell,
                    recipient,
                    spend_secret,
                    rho,
                    rseed,
                    note_domain,
                    authority_domain,
                    nullifier_domain,
                ))
            },
        )?;

        // Range-constrain value, cap slack, and value-1. The value-1 relation
        // makes zero impossible without requiring an inversion gadget.
        for (index, (ranged_value, target)) in [
            (self.value, value_cell.cell()),
            (slack_value, slack_cell.cell()),
            (prior_value, prior_cell.cell()),
        ]
        .into_iter()
        .enumerate()
        {
            let first = layouter.assign_region(
                || format!("phase9b range witness {index}"),
                |mut region| {
                    let mut first = None;
                    for i in 0..=RANGE_BITS {
                        let acc_value = if i == RANGE_BITS {
                            0
                        } else {
                            ranged_value >> i
                        };
                        let acc = region.assign_advice(
                            || "range accumulator",
                            config.range_acc,
                            i,
                            || Value::known(Fp::from(acc_value)),
                        )?;
                        if i == 0 {
                            first = Some(acc.clone());
                        }

                        if i < RANGE_BITS {
                            let bit_value = (ranged_value >> i) & 1;
                            region.assign_advice(
                                || "range bit",
                                config.range_bit,
                                i,
                                || Value::known(Fp::from(bit_value)),
                            )?;
                            config.range_select.enable(&mut region, i)?;
                        } else {
                            config.range_final_select.enable(&mut region, i)?;
                        }
                    }
                    Ok(first.expect("range starts at row zero"))
                },
            )?;
            layouter.assign_region(
                || format!("phase9b bind range witness {index}"),
                |mut region| {
                    let copied = first.copy_advice(
                        || "range first accumulator",
                        &mut region,
                        config.range_acc,
                        0,
                    )?;
                    region.constrain_equal(copied.cell(), target)
                },
            )?;
        }

        // Authority tag appears inside the note identity and is also public.
        let tag = hash_cells(
            &config,
            &mut layouter,
            authority_domain,
            spend_secret.clone(),
            "phase9b authority tag",
        )?;

        // Derive note identity from all private note fields.
        let h0 = hash_cells(
            &config,
            &mut layouter,
            note_domain,
            value_cell,
            "phase9b note value",
        )?;
        let h1 = hash_cells(
            &config,
            &mut layouter,
            h0,
            recipient,
            "phase9b note recipient",
        )?;
        let h2 = hash_cells(
            &config,
            &mut layouter,
            h1,
            tag.clone(),
            "phase9b note authority",
        )?;
        let h3 = hash_cells(&config, &mut layouter, h2, rho, "phase9b note rho")?;
        let identity = hash_cells(
            &config,
            &mut layouter,
            h3,
            rseed,
            "phase9b note randomness",
        )?;

        // Anchor branch uses the exact derived identity cell.
        let mut current = identity.clone();
        let mut current_value = self.native_note_identity();

        for level in 0..TREE_DEPTH {
            let sibling_value = self.siblings[level];
            let direction_value = self.directions[level];

            let (left_cell, right_cell) = layouter.assign_region(
                || format!("phase9b anchor path level {level}"),
                |mut region| {
                    config.path_select.enable(&mut region, 0)?;

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
                &format!("phase9b anchor parent {level}"),
            )?;

            current_value = if direction_value {
                poseidon_pair(sibling_value, current_value)
            } else {
                poseidon_pair(current_value, sibling_value)
            };
        }

        layouter.constrain_instance(current.cell(), config.instance, 0)?;
        layouter.constrain_instance(tag.cell(), config.instance, 1)?;

        // Nullifier branch uses the same derived identity cell.
        let note_key = hash_cells(
            &config,
            &mut layouter,
            spend_secret,
            identity,
            "phase9b note-bound secret",
        )?;
        let nf = hash_cells(
            &config,
            &mut layouter,
            nullifier_domain,
            note_key,
            "phase9b nullifier",
        )?;
        layouter.constrain_instance(nf.cell(), config.instance, 2)
    }
}
