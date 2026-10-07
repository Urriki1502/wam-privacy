//! Phase 10B: fixed-shape 2-input / 2-output shielded bundle relation.
//!
//! This circuit extends Phase 9C without changing the Phase 9C baseline.
//! It proves, in one relation:
//! - two private input note derivations;
//! - two Merkle membership paths against one public root;
//! - two private spend-authority bindings;
//! - two public nullifiers;
//! - in-circuit nullifier distinctness;
//! - two private output note derivations;
//! - two public output commitments;
//! - in-circuit output-commitment distinctness;
//! - aggregate value conservation with one explicit public fee;
//! - per-amount and aggregate WAM monetary-cap constraints.
//!
//! Public instances:
//! - row 0: shared input commitment-tree root;
//! - row 1: input 0 authority tag;
//! - row 2: input 0 nullifier;
//! - row 3: input 1 authority tag;
//! - row 4: input 1 nullifier;
//! - row 5: output 0 note commitment;
//! - row 6: output 1 note commitment;
//! - row 7: fee.
//!
//! This is a fixed-shape research circuit, not a WAM consensus encoding.

use halo2_gadgets::poseidon::{
    primitives::{ConstantLength, P128Pow5T3},
    Hash as PoseidonHash, Pow5Chip, Pow5Config,
};
use halo2_proofs::{
    arithmetic::Field,
    circuit::{AssignedCell, Layouter, SimpleFloorPlanner, Value},
    pasta::Fp,
    plonk::{
        Advice, Circuit, Column, ConstraintSystem, Error, Expression, Fixed, Instance, Selector,
    },
    poly::Rotation,
};

use crate::{
    anchor::TREE_DEPTH,
    note_action::{authority_tag, merkle_root, note_identity, nullifier, NOTE_DOMAIN},
    nullifier::{AUTHORITY_DOMAIN, NULLIFIER_DOMAIN},
    MAX_WAM_ATOMS,
};

const WIDTH: usize = 3;
const RATE: usize = 2;
const HASH_INPUTS: usize = 2;
const RANGE_BITS: usize = 64;

#[derive(Clone, Debug)]
pub struct BundleInput {
    pub value: u64,
    pub recipient_tag: Fp,
    pub spend_secret: Fp,
    pub rho: Fp,
    pub rseed: Fp,
    pub siblings: [Fp; TREE_DEPTH],
    pub directions: [bool; TREE_DEPTH],
}

impl BundleInput {
    pub fn identity(&self) -> Fp {
        note_identity(
            self.value,
            self.recipient_tag,
            authority_tag(self.spend_secret),
            self.rho,
            self.rseed,
        )
    }

    pub fn authority_tag(&self) -> Fp {
        authority_tag(self.spend_secret)
    }

    pub fn nullifier(&self) -> Fp {
        nullifier(self.spend_secret, self.identity())
    }

    pub fn root(&self) -> Fp {
        merkle_root(self.identity(), self.siblings, self.directions)
    }
}

#[derive(Clone, Debug)]
pub struct BundleOutput {
    pub value: u64,
    pub recipient_tag: Fp,
    pub spend_authority_tag: Fp,
    pub rho: Fp,
    pub rseed: Fp,
}

impl BundleOutput {
    pub fn identity(&self) -> Fp {
        note_identity(
            self.value,
            self.recipient_tag,
            self.spend_authority_tag,
            self.rho,
            self.rseed,
        )
    }
}

#[derive(Clone, Debug)]
pub struct BundleActionCircuit {
    pub inputs: [BundleInput; 2],
    pub outputs: [BundleOutput; 2],
    pub fee: u64,
}

impl Default for BundleActionCircuit {
    fn default() -> Self {
        Self {
            inputs: [
                BundleInput {
                    value: 4,
                    recipient_tag: Fp::from(11),
                    spend_secret: Fp::from(12),
                    rho: Fp::from(13),
                    rseed: Fp::from(14),
                    siblings: [Fp::zero(); TREE_DEPTH],
                    directions: [false; TREE_DEPTH],
                },
                BundleInput {
                    value: 5,
                    recipient_tag: Fp::from(21),
                    spend_secret: Fp::from(22),
                    rho: Fp::from(23),
                    rseed: Fp::from(24),
                    siblings: [Fp::zero(); TREE_DEPTH],
                    directions: [false; TREE_DEPTH],
                },
            ],
            outputs: [
                BundleOutput {
                    value: 3,
                    recipient_tag: Fp::from(31),
                    spend_authority_tag: Fp::from(32),
                    rho: Fp::from(33),
                    rseed: Fp::from(34),
                },
                BundleOutput {
                    value: 5,
                    recipient_tag: Fp::from(41),
                    spend_authority_tag: Fp::from(42),
                    rho: Fp::from(43),
                    rseed: Fp::from(44),
                },
            ],
            fee: 1,
        }
    }
}

impl BundleActionCircuit {
    pub fn public_inputs(&self) -> Vec<Fp> {
        vec![
            self.inputs[0].root(),
            self.inputs[0].authority_tag(),
            self.inputs[0].nullifier(),
            self.inputs[1].authority_tag(),
            self.inputs[1].nullifier(),
            self.outputs[0].identity(),
            self.outputs[1].identity(),
            Fp::from(self.fee),
        ]
    }

    pub fn input_total(&self) -> u64 {
        self.inputs[0].value.saturating_add(self.inputs[1].value)
    }

    pub fn output_total_with_fee(&self) -> u64 {
        self.outputs[0]
            .value
            .saturating_add(self.outputs[1].value)
            .saturating_add(self.fee)
    }
}

#[derive(Clone, Debug)]
pub struct BundleActionConfig {
    witness: Column<Advice>,
    input0_value: Column<Advice>,
    input1_value: Column<Advice>,
    output0_value: Column<Advice>,
    output1_value: Column<Advice>,
    fee: Column<Advice>,
    input_total: Column<Advice>,
    output_total: Column<Advice>,
    cap_value: Column<Advice>,
    cap_slack: Column<Advice>,
    value_minus_one: Column<Advice>,
    range_acc: Column<Advice>,
    range_bit: Column<Advice>,
    sibling: Column<Advice>,
    direction: Column<Advice>,
    left: Column<Advice>,
    right: Column<Advice>,
    distinct_left: Column<Advice>,
    distinct_right: Column<Advice>,
    distinct_inv: Column<Advice>,
    balance_select: Selector,
    cap_select: Selector,
    positive_select: Selector,
    range_select: Selector,
    range_final_select: Selector,
    path_select: Selector,
    distinct_select: Selector,
    instance: Column<Instance>,
    poseidon: Pow5Config<Fp, WIDTH, RATE>,
}

fn hash_cells(
    config: &BundleActionConfig,
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

fn range_bind(
    config: &BundleActionConfig,
    layouter: &mut impl Layouter<Fp>,
    value: u64,
    target: &AssignedCell<Fp, Fp>,
    label: &str,
) -> Result<(), Error> {
    layouter.assign_region(
        || format!("{label} range"),
        |mut region| {
            let mut first = None;
            for i in 0..=RANGE_BITS {
                let acc_value = if i == RANGE_BITS { 0 } else { value >> i };
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
                    let bit_value = (value >> i) & 1;
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

            region.constrain_equal(
                target.cell(),
                first.expect("range starts at row zero").cell(),
            )
        },
    )
}

fn constrain_amount(
    config: &BundleActionConfig,
    layouter: &mut impl Layouter<Fp>,
    value: u64,
    amount: &AssignedCell<Fp, Fp>,
    positive: bool,
    label: &str,
) -> Result<(), Error> {
    let slack_value = MAX_WAM_ATOMS.saturating_sub(value);
    let prior_value = value.saturating_sub(1);

    let (cap_cell, slack_cell, prior_cell) = layouter.assign_region(
        || format!("{label} cap"),
        |mut region| {
            config.cap_select.enable(&mut region, 0)?;
            if positive {
                config.positive_select.enable(&mut region, 0)?;
            }

            let cap_cell = region.assign_advice(
                || "capped amount",
                config.cap_value,
                0,
                || Value::known(Fp::from(value)),
            )?;
            let slack_cell = region.assign_advice(
                || "cap slack",
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

            region.constrain_equal(amount.cell(), cap_cell.cell())?;
            Ok((cap_cell, slack_cell, prior_cell))
        },
    )?;

    range_bind(
        config,
        layouter,
        value,
        &cap_cell,
        &format!("{label} value"),
    )?;
    range_bind(
        config,
        layouter,
        slack_value,
        &slack_cell,
        &format!("{label} slack"),
    )?;
    if positive {
        range_bind(
            config,
            layouter,
            prior_value,
            &prior_cell,
            &format!("{label} prior"),
        )?;
    }
    Ok(())
}

fn derive_input(
    config: &BundleActionConfig,
    layouter: &mut impl Layouter<Fp>,
    value: AssignedCell<Fp, Fp>,
    input: &BundleInput,
    label: &str,
) -> Result<
    (
        AssignedCell<Fp, Fp>,
        AssignedCell<Fp, Fp>,
        AssignedCell<Fp, Fp>,
    ),
    Error,
> {
    let (
        recipient,
        spend_secret,
        rho,
        rseed,
        note_domain,
        authority_domain,
        nullifier_domain,
    ) = layouter.assign_region(
        || format!("{label} private fields"),
        |mut region| {
            let recipient = region.assign_advice(
                || "recipient tag",
                config.witness,
                0,
                || Value::known(input.recipient_tag),
            )?;
            let spend_secret = region.assign_advice(
                || "spend secret",
                config.witness,
                1,
                || Value::known(input.spend_secret),
            )?;
            let rho = region.assign_advice(
                || "rho",
                config.witness,
                2,
                || Value::known(input.rho),
            )?;
            let rseed = region.assign_advice(
                || "rseed",
                config.witness,
                3,
                || Value::known(input.rseed),
            )?;
            let note_domain = region.assign_advice(
                || "note domain",
                config.witness,
                4,
                || Value::known(Fp::from(NOTE_DOMAIN)),
            )?;
            let authority_domain = region.assign_advice(
                || "authority domain",
                config.witness,
                5,
                || Value::known(Fp::from(AUTHORITY_DOMAIN)),
            )?;
            let nullifier_domain = region.assign_advice(
                || "nullifier domain",
                config.witness,
                6,
                || Value::known(Fp::from(NULLIFIER_DOMAIN)),
            )?;
            Ok((
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

    let authority = hash_cells(
        config,
        layouter,
        authority_domain,
        spend_secret.clone(),
        &format!("{label} authority"),
    )?;

    let h0 = hash_cells(
        config,
        layouter,
        note_domain,
        value,
        &format!("{label} note domain/value"),
    )?;
    let h1 = hash_cells(
        config,
        layouter,
        h0,
        recipient,
        &format!("{label} recipient"),
    )?;
    let h2 = hash_cells(
        config,
        layouter,
        h1,
        authority.clone(),
        &format!("{label} authority tag"),
    )?;
    let h3 = hash_cells(config, layouter, h2, rho, &format!("{label} rho"))?;
    let identity = hash_cells(
        config,
        layouter,
        h3,
        rseed,
        &format!("{label} randomness"),
    )?;

    let root = anchor_identity(
        config,
        layouter,
        identity.clone(),
        input.identity(),
        &input.siblings,
        &input.directions,
        &format!("{label} anchor"),
    )?;

    let note_key = hash_cells(
        config,
        layouter,
        spend_secret,
        identity,
        &format!("{label} note-bound secret"),
    )?;
    let nf = hash_cells(
        config,
        layouter,
        nullifier_domain,
        note_key,
        &format!("{label} nullifier"),
    )?;

    Ok((root, authority, nf))
}

fn derive_output(
    config: &BundleActionConfig,
    layouter: &mut impl Layouter<Fp>,
    value: AssignedCell<Fp, Fp>,
    output: &BundleOutput,
    label: &str,
) -> Result<AssignedCell<Fp, Fp>, Error> {
    let (recipient, authority, rho, rseed, note_domain) = layouter.assign_region(
        || format!("{label} private fields"),
        |mut region| {
            let recipient = region.assign_advice(
                || "recipient tag",
                config.witness,
                0,
                || Value::known(output.recipient_tag),
            )?;
            let authority = region.assign_advice(
                || "spend authority tag",
                config.witness,
                1,
                || Value::known(output.spend_authority_tag),
            )?;
            let rho = region.assign_advice(
                || "rho",
                config.witness,
                2,
                || Value::known(output.rho),
            )?;
            let rseed = region.assign_advice(
                || "rseed",
                config.witness,
                3,
                || Value::known(output.rseed),
            )?;
            let note_domain = region.assign_advice(
                || "note domain",
                config.witness,
                4,
                || Value::known(Fp::from(NOTE_DOMAIN)),
            )?;
            Ok((recipient, authority, rho, rseed, note_domain))
        },
    )?;

    let h0 = hash_cells(
        config,
        layouter,
        note_domain,
        value,
        &format!("{label} note domain/value"),
    )?;
    let h1 = hash_cells(
        config,
        layouter,
        h0,
        recipient,
        &format!("{label} recipient"),
    )?;
    let h2 = hash_cells(
        config,
        layouter,
        h1,
        authority,
        &format!("{label} authority tag"),
    )?;
    let h3 = hash_cells(config, layouter, h2, rho, &format!("{label} rho"))?;
    hash_cells(
        config,
        layouter,
        h3,
        rseed,
        &format!("{label} randomness"),
    )
}

fn anchor_identity(
    config: &BundleActionConfig,
    layouter: &mut impl Layouter<Fp>,
    mut current: AssignedCell<Fp, Fp>,
    mut current_value: Fp,
    siblings: &[Fp; TREE_DEPTH],
    directions: &[bool; TREE_DEPTH],
    label: &str,
) -> Result<AssignedCell<Fp, Fp>, Error> {
    for level in 0..TREE_DEPTH {
        let sibling_value = siblings[level];
        let direction_value = directions[level];

        let (left_cell, right_cell) = layouter.assign_region(
            || format!("{label} level {level}"),
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
            config,
            layouter,
            left_cell,
            right_cell,
            &format!("{label} parent {level}"),
        )?;
        current_value = if direction_value {
            crate::note_action::poseidon_pair(sibling_value, current_value)
        } else {
            crate::note_action::poseidon_pair(current_value, sibling_value)
        };
    }
    Ok(current)
}

fn constrain_distinct(
    config: &BundleActionConfig,
    layouter: &mut impl Layouter<Fp>,
    left: &AssignedCell<Fp, Fp>,
    right: &AssignedCell<Fp, Fp>,
    left_value: Fp,
    right_value: Fp,
    label: &str,
) -> Result<(), Error> {
    let difference = left_value - right_value;
    let inverse = Option::<Fp>::from(difference.invert()).unwrap_or(Fp::zero());

    layouter.assign_region(
        || format!("{label} distinctness"),
        |mut region| {
            config.distinct_select.enable(&mut region, 0)?;
            left.copy_advice(|| "distinct left", &mut region, config.distinct_left, 0)?;
            right.copy_advice(|| "distinct right", &mut region, config.distinct_right, 0)?;
            region.assign_advice(
                || "difference inverse",
                config.distinct_inv,
                0,
                || Value::known(inverse),
            )?;
            Ok(())
        },
    )
}

impl Circuit<Fp> for BundleActionCircuit {
    type Config = BundleActionConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let witness = meta.advice_column();
        let input0_value = meta.advice_column();
        let input1_value = meta.advice_column();
        let output0_value = meta.advice_column();
        let output1_value = meta.advice_column();
        let fee = meta.advice_column();
        let input_total = meta.advice_column();
        let output_total = meta.advice_column();
        let cap_value = meta.advice_column();
        let cap_slack = meta.advice_column();
        let value_minus_one = meta.advice_column();
        let range_acc = meta.advice_column();
        let range_bit = meta.advice_column();
        let sibling = meta.advice_column();
        let direction = meta.advice_column();
        let left = meta.advice_column();
        let right = meta.advice_column();
        let distinct_left = meta.advice_column();
        let distinct_right = meta.advice_column();
        let distinct_inv = meta.advice_column();
        let instance = meta.instance_column();

        for column in [
            witness,
            input0_value,
            input1_value,
            output0_value,
            output1_value,
            fee,
            input_total,
            output_total,
            cap_value,
            cap_slack,
            value_minus_one,
            range_acc,
            sibling,
            direction,
            left,
            right,
            distinct_left,
            distinct_right,
            distinct_inv,
        ] {
            meta.enable_equality(column);
        }
        meta.enable_equality(instance);

        let balance_select = meta.selector();
        let cap_select = meta.selector();
        let positive_select = meta.selector();
        let range_select = meta.selector();
        let range_final_select = meta.selector();
        let path_select = meta.selector();
        let distinct_select = meta.selector();

        meta.create_gate("phase10b fixed bundle conservation", |meta| {
            let s = meta.query_selector(balance_select);
            let in0 = meta.query_advice(input0_value, Rotation::cur());
            let in1 = meta.query_advice(input1_value, Rotation::cur());
            let out0 = meta.query_advice(output0_value, Rotation::cur());
            let out1 = meta.query_advice(output1_value, Rotation::cur());
            let fee_v = meta.query_advice(fee, Rotation::cur());
            let in_total = meta.query_advice(input_total, Rotation::cur());
            let out_total = meta.query_advice(output_total, Rotation::cur());

            vec![
                s.clone() * (in_total.clone() - in0 - in1),
                s.clone() * (out_total.clone() - out0 - out1 - fee_v),
                s * (in_total - out_total),
            ]
        });

        meta.create_gate("phase10b exact wam monetary cap", |meta| {
            let s = meta.query_selector(cap_select);
            let value = meta.query_advice(cap_value, Rotation::cur());
            let slack = meta.query_advice(cap_slack, Rotation::cur());
            let cap = Expression::Constant(Fp::from(MAX_WAM_ATOMS));
            vec![s * (value + slack - cap)]
        });

        meta.create_gate("phase10b positive shielded value", |meta| {
            let s = meta.query_selector(positive_select);
            let value = meta.query_advice(cap_value, Rotation::cur());
            let prior = meta.query_advice(value_minus_one, Rotation::cur());
            vec![s * (value - prior - Expression::Constant(Fp::one()))]
        });

        meta.create_gate("phase10b 64-bit decomposition", |meta| {
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

        meta.create_gate("phase10b range termination", |meta| {
            let s = meta.query_selector(range_final_select);
            let acc = meta.query_advice(range_acc, Rotation::cur());
            vec![s * acc]
        });

        meta.create_gate("phase10b merkle child ordering", |meta| {
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

        meta.create_gate("phase10b distinct pair", |meta| {
            let s = meta.query_selector(distinct_select);
            let left_v = meta.query_advice(distinct_left, Rotation::cur());
            let right_v = meta.query_advice(distinct_right, Rotation::cur());
            let inv = meta.query_advice(distinct_inv, Rotation::cur());
            vec![s * ((left_v - right_v) * inv - Expression::Constant(Fp::one()))]
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

        BundleActionConfig {
            witness,
            input0_value,
            input1_value,
            output0_value,
            output1_value,
            fee,
            input_total,
            output_total,
            cap_value,
            cap_slack,
            value_minus_one,
            range_acc,
            range_bit,
            sibling,
            direction,
            left,
            right,
            distinct_left,
            distinct_right,
            distinct_inv,
            balance_select,
            cap_select,
            positive_select,
            range_select,
            range_final_select,
            path_select,
            distinct_select,
            instance,
            poseidon,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        let input_total_native = self.input_total();
        let output_total_native = self.output_total_with_fee();

        let (
            input0_value,
            input1_value,
            output0_value,
            output1_value,
            fee,
            input_total,
            output_total,
        ) = layouter.assign_region(
            || "phase10b aggregate value relation",
            |mut region| {
                config.balance_select.enable(&mut region, 0)?;

                let input0 = region.assign_advice(
                    || "input 0 value",
                    config.input0_value,
                    0,
                    || Value::known(Fp::from(self.inputs[0].value)),
                )?;
                let input1 = region.assign_advice(
                    || "input 1 value",
                    config.input1_value,
                    0,
                    || Value::known(Fp::from(self.inputs[1].value)),
                )?;
                let output0 = region.assign_advice(
                    || "output 0 value",
                    config.output0_value,
                    0,
                    || Value::known(Fp::from(self.outputs[0].value)),
                )?;
                let output1 = region.assign_advice(
                    || "output 1 value",
                    config.output1_value,
                    0,
                    || Value::known(Fp::from(self.outputs[1].value)),
                )?;
                let fee = region.assign_advice(
                    || "public fee witness",
                    config.fee,
                    0,
                    || Value::known(Fp::from(self.fee)),
                )?;
                let input_total = region.assign_advice(
                    || "input aggregate",
                    config.input_total,
                    0,
                    || Value::known(Fp::from(input_total_native)),
                )?;
                let output_total = region.assign_advice(
                    || "output aggregate",
                    config.output_total,
                    0,
                    || Value::known(Fp::from(output_total_native)),
                )?;

                Ok((
                    input0,
                    input1,
                    output0,
                    output1,
                    fee,
                    input_total,
                    output_total,
                ))
            },
        )?;

        constrain_amount(
            &config,
            &mut layouter,
            self.inputs[0].value,
            &input0_value,
            true,
            "phase10b input 0",
        )?;
        constrain_amount(
            &config,
            &mut layouter,
            self.inputs[1].value,
            &input1_value,
            true,
            "phase10b input 1",
        )?;
        constrain_amount(
            &config,
            &mut layouter,
            self.outputs[0].value,
            &output0_value,
            true,
            "phase10b output 0",
        )?;
        constrain_amount(
            &config,
            &mut layouter,
            self.outputs[1].value,
            &output1_value,
            true,
            "phase10b output 1",
        )?;
        constrain_amount(
            &config,
            &mut layouter,
            self.fee,
            &fee,
            false,
            "phase10b fee",
        )?;
        constrain_amount(
            &config,
            &mut layouter,
            input_total_native,
            &input_total,
            true,
            "phase10b input aggregate",
        )?;
        constrain_amount(
            &config,
            &mut layouter,
            output_total_native,
            &output_total,
            true,
            "phase10b output aggregate",
        )?;

        let (root0, authority0, nf0) = derive_input(
            &config,
            &mut layouter,
            input0_value,
            &self.inputs[0],
            "phase10b input 0",
        )?;
        let (root1, authority1, nf1) = derive_input(
            &config,
            &mut layouter,
            input1_value,
            &self.inputs[1],
            "phase10b input 1",
        )?;

        // Both spends must belong to the same public anchor.
        layouter.constrain_instance(root0.cell(), config.instance, 0)?;
        layouter.constrain_instance(root1.cell(), config.instance, 0)?;
        layouter.constrain_instance(authority0.cell(), config.instance, 1)?;
        layouter.constrain_instance(nf0.cell(), config.instance, 2)?;
        layouter.constrain_instance(authority1.cell(), config.instance, 3)?;
        layouter.constrain_instance(nf1.cell(), config.instance, 4)?;

        constrain_distinct(
            &config,
            &mut layouter,
            &nf0,
            &nf1,
            self.inputs[0].nullifier(),
            self.inputs[1].nullifier(),
            "phase10b nullifiers",
        )?;

        let output0 = derive_output(
            &config,
            &mut layouter,
            output0_value,
            &self.outputs[0],
            "phase10b output 0",
        )?;
        let output1 = derive_output(
            &config,
            &mut layouter,
            output1_value,
            &self.outputs[1],
            "phase10b output 1",
        )?;

        layouter.constrain_instance(output0.cell(), config.instance, 5)?;
        layouter.constrain_instance(output1.cell(), config.instance, 6)?;
        layouter.constrain_instance(fee.cell(), config.instance, 7)?;

        constrain_distinct(
            &config,
            &mut layouter,
            &output0,
            &output1,
            self.outputs[0].identity(),
            self.outputs[1].identity(),
            "phase10b output commitments",
        )
    }
}
