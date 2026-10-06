//! Phase 8-A: isolated Halo2 balance-circuit prototype.
//!
//! This crate deliberately proves only a narrow arithmetic relation:
//!
//! spent + transparent_in = created + transparent_out + fee
//!
//! It does NOT yet prove:
//! - note membership;
//! - commitment-tree anchoring;
//! - nullifier correctness;
//! - spend-authority binding;
//! - amount range constraints;
//! - note encryption/viewing semantics.
//!
//! Those omissions are explicit blockers for any stronger claim.

use halo2_proofs::{
    circuit::{Layouter, SimpleFloorPlanner, Value},
    pasta::Fp,
    plonk::{Advice, Circuit, Column, ConstraintSystem, Error, Selector},
    poly::Rotation,
};

#[derive(Clone, Debug)]
pub struct BalanceConfig {
    spent: Column<Advice>,
    transparent_in: Column<Advice>,
    created: Column<Advice>,
    transparent_out: Column<Advice>,
    fee: Column<Advice>,
    selector: Selector,
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
        let selector = meta.selector();

        meta.create_gate("wam shielded value conservation", |meta| {
            let s = meta.query_selector(selector);
            let spent_v = meta.query_advice(spent, Rotation::cur());
            let tin_v = meta.query_advice(transparent_in, Rotation::cur());
            let created_v = meta.query_advice(created, Rotation::cur());
            let tout_v = meta.query_advice(transparent_out, Rotation::cur());
            let fee_v = meta.query_advice(fee, Rotation::cur());

            vec![s * (spent_v + tin_v - created_v - tout_v - fee_v)]
        });

        BalanceConfig {
            spent,
            transparent_in,
            created,
            transparent_out,
            fee,
            selector,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        layouter.assign_region(
            || "wam balance witness",
            |mut region| {
                config.selector.enable(&mut region, 0)?;

                region.assign_advice(
                    || "spent",
                    config.spent,
                    0,
                    || Value::known(Fp::from(self.spent)),
                )?;
                region.assign_advice(
                    || "transparent_in",
                    config.transparent_in,
                    0,
                    || Value::known(Fp::from(self.transparent_in)),
                )?;
                region.assign_advice(
                    || "created",
                    config.created,
                    0,
                    || Value::known(Fp::from(self.created)),
                )?;
                region.assign_advice(
                    || "transparent_out",
                    config.transparent_out,
                    0,
                    || Value::known(Fp::from(self.transparent_out)),
                )?;
                region.assign_advice(
                    || "fee",
                    config.fee,
                    0,
                    || Value::known(Fp::from(self.fee)),
                )?;

                Ok(())
            },
        )
    }
}
