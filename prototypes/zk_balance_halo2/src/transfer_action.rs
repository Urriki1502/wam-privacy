//! Phase 9C: integrated shielded transfer relation.
//!
//! This circuit composes, in one proof:
//! - input note derivation;
//! - input-note Merkle membership;
//! - spend-authority binding;
//! - nullifier derivation;
//! - output note derivation;
//! - value conservation.
//!
//! The research relation is intentionally narrow: one shielded input,
//! one shielded output, and one explicit fee.
//!
//! Public instances:
//! - row 0: input commitment-tree root;
//! - row 1: input authority tag;
//! - row 2: input nullifier;
//! - row 3: output note commitment;
//! - row 4: fee.
//!
//! This is an isolated research circuit, not a final WAM consensus encoding.

use halo2_gadgets::poseidon::{
    primitives::{ConstantLength, P128Pow5T3},
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
    note_action::{authority_tag, merkle_root, note_identity, nullifier, NOTE_DOMAIN},
    nullifier::{AUTHORITY_DOMAIN, NULLIFIER_DOMAIN},
    MAX_WAM_ATOMS,
};

const WIDTH: usize = 3;
const RATE: usize = 2;
const HASH_INPUTS: usize = 2;
const RANGE_BITS: usize = 64;

#[derive(Clone, Debug)]
pub struct TransferActionConfig {
    witness: Column<Advice>,
    input_value: Column<Advice>,
    output_value: Column<Advice>,
    fee: Column<Advice>,
    cap_value: Column<Advice>,
    cap_slack: Column<Advice>,
    value_minus_one: Column<Advice>,
    range_acc: Column<Advice>,
    range_bit: Column<Advice>,
    sibling: Column<Advice>,
    direction: Column<Advice>,
    left: Column<Advice>,
    right: Column<Advice>,
    balance_select: Selector,
    cap_select: Selector,
    positive_select: Selector,
    range_select: Selector,
    range_final_select: Selector,
    path_select: Selector,
    instance: Column<Instance>,
    poseidon: Pow5Config<Fp, WIDTH, RATE>,
}

#[derive(Clone, Debug)]
pub struct TransferActionCircuit {
    pub input_value: u64,
    pub input_recipient_tag: Fp,
    pub spend_secret: Fp,
    pub input_rho: Fp,
    pub input_rseed: Fp,
    pub siblings: [Fp; TREE_DEPTH],
    pub directions: [bool; TREE_DEPTH],

    pub output_value: u64,
    pub output_recipient_tag: Fp,
    pub output_spend_authority_tag: Fp,
    pub output_rho: Fp,
    pub output_rseed: Fp,

    pub fee: u64,
}

impl Default for TransferActionCircuit {
    fn default() -> Self {
        Self {
            input_value: 2,
            input_recipient_tag: Fp::zero(),
            spend_secret: Fp::zero(),
            input_rho: Fp::zero(),
            input_rseed: Fp::zero(),
            siblings: [Fp::zero(); TREE_DEPTH],
            directions: [false; TREE_DEPTH],
            output_value: 1,
            output_recipient_tag: Fp::zero(),
            output_spend_authority_tag: Fp::zero(),
            output_rho: Fp::zero(),
            output_rseed: Fp::zero(),
            fee: 1,
        }
    }
}

impl TransferActionCircuit {
    pub fn input_identity(&self) -> Fp {
        let tag = authority_tag(self.spend_secret);
        note_identity(
            self.input_value,
            self.input_recipient_tag,
            tag,
            self.input_rho,
            self.input_rseed,
        )
    }

    pub fn output_identity(&self) -> Fp {
        note_identity(
            self.output_value,
            self.output_recipient_tag,
            self.output_spend_authority_tag,
            self.output_rho,
            self.output_rseed,
        )
    }

    pub fn public_inputs(&self) -> Vec<Fp> {
        let input_identity = self.input_identity();
        vec![
            merkle_root(input_identity, self.siblings, self.directions),
            authority_tag(self.spend_secret),
            nullifier(self.spend_secret, input_identity),
            self.output_identity(),
            Fp::from(self.fee),
        ]
    }
}

fn hash_cells(
    config: &TransferActionConfig,
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
    config: &TransferActionConfig,
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
    config: &TransferActionConfig,
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

impl Circuit<Fp> for TransferActionCircuit {
    type Config = TransferActionConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let witness = meta.advice_column();
        let input_value = meta.advice_column();
        let output_value = meta.advice_column();
        let fee = meta.advice_column();
        let cap_value = meta.advice_column();
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
            input_value,
            output_value,
            fee,
            cap_value,
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

        let balance_select = meta.selector();
        let cap_select = meta.selector();
        let positive_select = meta.selector();
        let range_select = meta.selector();
        let range_final_select = meta.selector();
        let path_select = meta.selector();

        meta.create_gate("phase9c shielded value conservation", |meta| {
            let s = meta.query_selector(balance_select);
            let input = meta.query_advice(input_value, Rotation::cur());
            let output = meta.query_advice(output_value, Rotation::cur());
            let fee_v = meta.query_advice(fee, Rotation::cur());
            vec![s * (input - output - fee_v)]
        });

        meta.create_gate("phase9c exact wam monetary cap", |meta| {
            let s = meta.query_selector(cap_select);
            let value = meta.query_advice(cap_value, Rotation::cur());
            let slack = meta.query_advice(cap_slack, Rotation::cur());
            let cap = Expression::Constant(Fp::from(MAX_WAM_ATOMS));
            vec![s * (value + slack - cap)]
        });

        meta.create_gate("phase9c positive shielded value", |meta| {
            let s = meta.query_selector(positive_select);
            let value = meta.query_advice(cap_value, Rotation::cur());
            let prior = meta.query_advice(value_minus_one, Rotation::cur());
            vec![s * (value - prior - Expression::Constant(Fp::one()))]
        });

        meta.create_gate("phase9c 64-bit decomposition", |meta| {
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

        meta.create_gate("phase9c range termination", |meta| {
            let s = meta.query_selector(range_final_select);
            let acc = meta.query_advice(range_acc, Rotation::cur());
            vec![s * acc]
        });

        meta.create_gate("phase9c merkle child ordering", |meta| {
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

        TransferActionConfig {
            witness,
            input_value,
            output_value,
            fee,
            cap_value,
            cap_slack,
            value_minus_one,
            range_acc,
            range_bit,
            sibling,
            direction,
            left,
            right,
            balance_select,
            cap_select,
            positive_select,
            range_select,
            range_final_select,
            path_select,
            instance,
            poseidon,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        let (input_value, output_value, fee) = layouter.assign_region(
            || "phase9c value relation",
            |mut region| {
                config.balance_select.enable(&mut region, 0)?;

                let input = region.assign_advice(
                    || "input note value",
                    config.input_value,
                    0,
                    || Value::known(Fp::from(self.input_value)),
                )?;
                let output = region.assign_advice(
                    || "output note value",
                    config.output_value,
                    0,
                    || Value::known(Fp::from(self.output_value)),
                )?;
                let fee = region.assign_advice(
                    || "public fee witness",
                    config.fee,
                    0,
                    || Value::known(Fp::from(self.fee)),
                )?;
                Ok((input, output, fee))
            },
        )?;

        constrain_amount(
            &config,
            &mut layouter,
            self.input_value,
            &input_value,
            true,
            "phase9c input",
        )?;
        constrain_amount(
            &config,
            &mut layouter,
            self.output_value,
            &output_value,
            true,
            "phase9c output",
        )?;
        constrain_amount(&config, &mut layouter, self.fee, &fee, false, "phase9c fee")?;

        let (
            input_recipient,
            spend_secret,
            input_rho,
            input_rseed,
            output_recipient,
            output_authority_tag,
            output_rho,
            output_rseed,
            note_domain,
            authority_domain,
            nullifier_domain,
        ) = layouter.assign_region(
            || "phase9c private note fields",
            |mut region| {
                let input_recipient = region.assign_advice(
                    || "input recipient tag",
                    config.witness,
                    0,
                    || Value::known(self.input_recipient_tag),
                )?;
                let spend_secret = region.assign_advice(
                    || "input spend secret",
                    config.witness,
                    1,
                    || Value::known(self.spend_secret),
                )?;
                let input_rho = region.assign_advice(
                    || "input rho",
                    config.witness,
                    2,
                    || Value::known(self.input_rho),
                )?;
                let input_rseed = region.assign_advice(
                    || "input rseed",
                    config.witness,
                    3,
                    || Value::known(self.input_rseed),
                )?;

                let output_recipient = region.assign_advice(
                    || "output recipient tag",
                    config.witness,
                    4,
                    || Value::known(self.output_recipient_tag),
                )?;
                let output_authority_tag = region.assign_advice(
                    || "output spend authority tag",
                    config.witness,
                    5,
                    || Value::known(self.output_spend_authority_tag),
                )?;
                let output_rho = region.assign_advice(
                    || "output rho",
                    config.witness,
                    6,
                    || Value::known(self.output_rho),
                )?;
                let output_rseed = region.assign_advice(
                    || "output rseed",
                    config.witness,
                    7,
                    || Value::known(self.output_rseed),
                )?;

                let note_domain = region.assign_advice_from_constant(
                    || "note domain",
                    config.witness,
                    8,
                    Fp::from(NOTE_DOMAIN),
                )?;
                let authority_domain = region.assign_advice_from_constant(
                    || "authority domain",
                    config.witness,
                    9,
                    Fp::from(AUTHORITY_DOMAIN),
                )?;
                let nullifier_domain = region.assign_advice_from_constant(
                    || "nullifier domain",
                    config.witness,
                    10,
                    Fp::from(NULLIFIER_DOMAIN),
                )?;

                Ok((
                    input_recipient,
                    spend_secret,
                    input_rho,
                    input_rseed,
                    output_recipient,
                    output_authority_tag,
                    output_rho,
                    output_rseed,
                    note_domain,
                    authority_domain,
                    nullifier_domain,
                ))
            },
        )?;

        // Input authority and note identity.
        let input_authority = hash_cells(
            &config,
            &mut layouter,
            authority_domain,
            spend_secret.clone(),
            "phase9c input authority",
        )?;

        let input_h0 = hash_cells(
            &config,
            &mut layouter,
            note_domain.clone(),
            input_value,
            "phase9c input note domain/value",
        )?;
        let input_h1 = hash_cells(
            &config,
            &mut layouter,
            input_h0,
            input_recipient,
            "phase9c input recipient",
        )?;
        let input_h2 = hash_cells(
            &config,
            &mut layouter,
            input_h1,
            input_authority.clone(),
            "phase9c input authority tag",
        )?;
        let input_h3 = hash_cells(
            &config,
            &mut layouter,
            input_h2,
            input_rho,
            "phase9c input rho",
        )?;
        let input_identity = hash_cells(
            &config,
            &mut layouter,
            input_h3,
            input_rseed,
            "phase9c input randomness",
        )?;

        // Anchor the exact input identity cell.
        let mut current = input_identity.clone();
        let mut current_value = self.input_identity();

        for level in 0..TREE_DEPTH {
            let sibling_value = self.siblings[level];
            let direction_value = self.directions[level];

            let (left_cell, right_cell) = layouter.assign_region(
                || format!("phase9c anchor path level {level}"),
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
                &format!("phase9c anchor parent {level}"),
            )?;

            current_value = if direction_value {
                crate::note_action::poseidon_pair(sibling_value, current_value)
            } else {
                crate::note_action::poseidon_pair(current_value, sibling_value)
            };
        }

        layouter.constrain_instance(current.cell(), config.instance, 0)?;
        layouter.constrain_instance(input_authority.cell(), config.instance, 1)?;

        // Nullifier uses the exact same input identity cell.
        let note_key = hash_cells(
            &config,
            &mut layouter,
            spend_secret,
            input_identity,
            "phase9c input note-bound secret",
        )?;
        let nf = hash_cells(
            &config,
            &mut layouter,
            nullifier_domain,
            note_key,
            "phase9c input nullifier",
        )?;
        layouter.constrain_instance(nf.cell(), config.instance, 2)?;

        // Output commitment uses the exact output value cell that participated
        // in the conservation equation.
        let output_h0 = hash_cells(
            &config,
            &mut layouter,
            note_domain,
            output_value,
            "phase9c output note domain/value",
        )?;
        let output_h1 = hash_cells(
            &config,
            &mut layouter,
            output_h0,
            output_recipient,
            "phase9c output recipient",
        )?;
        let output_h2 = hash_cells(
            &config,
            &mut layouter,
            output_h1,
            output_authority_tag,
            "phase9c output authority tag",
        )?;
        let output_h3 = hash_cells(
            &config,
            &mut layouter,
            output_h2,
            output_rho,
            "phase9c output rho",
        )?;
        let output_identity = hash_cells(
            &config,
            &mut layouter,
            output_h3,
            output_rseed,
            "phase9c output randomness",
        )?;
        layouter.constrain_instance(output_identity.cell(), config.instance, 3)?;

        // Fee is explicit and public so an external transaction layer can bind
        // the same fee into its own serialization later.
        layouter.constrain_instance(fee.cell(), config.instance, 4)
    }
}
