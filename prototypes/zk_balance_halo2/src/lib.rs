//! Phase 8-B: isolated Halo2 balance circuit with in-circuit 64-bit ranges.
//!
//! The circuit enforces:
//!
//! spent + transparent_in = created + transparent_out + fee
//!
//! and independently constrains each amount witness to a 64-bit decomposition.
//!
//! It still does NOT prove:
//! - WAM's exact monetary cap (22M * 1e8);
//! - note membership / Merkle anchoring;
//! - nullifier correctness;
//! - spend-authority binding;
//! - note encryption / viewing semantics;
//! - production proof-system integration.

use halo2_proofs::{
    circuit::{Layouter, SimpleFloorPlanner, Value},
    pasta::Fp,
    plonk::{Advice, Circuit, Column, ConstraintSystem, Error, Expression, Selector},
    poly::Rotation,
};

const RANGE_BITS: usize = 64;

#[derive(Clone, Debug)]
pub struct BalanceConfig {
    spent: Column<Advice>,
    transparent_in: Column<Advice>,
    created: Column<Advice>,
    transparent_out: Column<Advice>,
    fee: Column<Advice>,
    range_acc: Column<Advice>,
    range_bit: Column<Advice>,
    balance_selector: Selector,
    range_selector: Selector,
    range_final_selector: Selector,
}

#[derive(Clone, Debug, Default)]
pub struct BalanceCircuit {
    pub spent: u64,
    pub transparent_in: u64,
    pub created: u64,
    pub transparent_out: u64,
    pub fee: u64,
}

impl BalanceCircuit {
    pub fn lhs(&self) -> u128 {
        self.spent as u128 + self.transparent_in as u128
    }

    pub fn rhs(&self) -> u128 {
        self.created as u128 + self.transparent_out as u128 + self.fee as u128
    }

    fn values(&self) -> [u64; 5] {
        [
            self.spent,
            self.transparent_in,
            self.created,
            self.transparent_out,
            self.fee,
        ]
    }
}

impl Circuit<Fp> for BalanceCircuit {
    type Config = BalanceConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let spent = meta.advice_column();
        let transparent_in = meta.advice_column();
        let created = meta.advice_column();
        let transparent_out = meta.advice_column();
        let fee = meta.advice_column();
        let range_acc = meta.advice_column();
        let range_bit = meta.advice_column();

        for column in [
            spent,
            transparent_in,
            created,
            transparent_out,
            fee,
            range_acc,
        ] {
            meta.enable_equality(column);
        }

        let balance_selector = meta.selector();
        let range_selector = meta.selector();
        let range_final_selector = meta.selector();

        meta.create_gate("wam shielded value conservation", |meta| {
            let s = meta.query_selector(balance_selector);
            let spent_v = meta.query_advice(spent, Rotation::cur());
            let tin_v = meta.query_advice(transparent_in, Rotation::cur());
            let created_v = meta.query_advice(created, Rotation::cur());
            let tout_v = meta.query_advice(transparent_out, Rotation::cur());
            let fee_v = meta.query_advice(fee, Rotation::cur());

            vec![s * (spent_v + tin_v - created_v - tout_v - fee_v)]
        });

        meta.create_gate("64-bit amount decomposition", |meta| {
            let s = meta.query_selector(range_selector);
            let acc = meta.query_advice(range_acc, Rotation::cur());
            let next = meta.query_advice(range_acc, Rotation::next());
            let bit = meta.query_advice(range_bit, Rotation::cur());
            let one = Expression::Constant(Fp::from(1));
            let two = Expression::Constant(Fp::from(2));

            vec![
                s.clone() * (acc - bit.clone() - two * next),
                s * bit.clone() * (bit - one),
            ]
        });

        meta.create_gate("64-bit decomposition terminates", |meta| {
            let s = meta.query_selector(range_final_selector);
            let acc = meta.query_advice(range_acc, Rotation::cur());
            vec![s * acc]
        });

        BalanceConfig {
            spent,
            transparent_in,
            created,
            transparent_out,
            fee,
            range_acc,
            range_bit,
            balance_selector,
            range_selector,
            range_final_selector,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        layouter.assign_region(
            || "wam range-constrained balance witness",
            |mut region| {
                config.balance_selector.enable(&mut region, 0)?;

                let columns = [
                    config.spent,
                    config.transparent_in,
                    config.created,
                    config.transparent_out,
                    config.fee,
                ];
                let values = self.values();
                let mut amount_cells = Vec::with_capacity(values.len());

                for (column, value) in columns.into_iter().zip(values) {
                    amount_cells.push(region.assign_advice(
                        || "balance amount",
                        column,
                        0,
                        || Value::known(Fp::from(value)),
                    )?);
                }

                // Each witness is copied into a 64-step little-endian
                // decomposition:
                //
                //   acc_i = bit_i + 2 * acc_{i+1}
                //
                // with bit_i boolean and acc_64 = 0.
                //
                // This makes the field witness itself, rather than only the
                // host-side Rust type, prove that it fits in 64 bits.
                for (index, value) in values.into_iter().enumerate() {
                    let start = 2 + index * (RANGE_BITS + 1);
                    let mut first_acc = None;

                    for i in 0..=RANGE_BITS {
                        let acc_value = if i == RANGE_BITS { 0 } else { value >> i };
                        let acc = region.assign_advice(
                            || "range accumulator",
                            config.range_acc,
                            start + i,
                            || Value::known(Fp::from(acc_value)),
                        )?;

                        if i == 0 {
                            first_acc = Some(acc.clone());
                        }

                        if i < RANGE_BITS {
                            let bit_value = (value >> i) & 1;
                            region.assign_advice(
                                || "range bit",
                                config.range_bit,
                                start + i,
                                || Value::known(Fp::from(bit_value)),
                            )?;
                            config.range_selector.enable(&mut region, start + i)?;
                        } else {
                            config.range_final_selector.enable(&mut region, start + i)?;
                        }
                    }

                    region.constrain_equal(
                        amount_cells[index].cell(),
                        first_acc.expect("range accumulator exists").cell(),
                    )?;
                }

                Ok(())
            },
        )
    }
}
