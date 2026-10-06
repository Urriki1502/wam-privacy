//! Phase 8-D: isolated spend-authority / nullifier relation.
//!
//! This circuit proves two circuit-native relations with private witnesses:
//!
//! authority_tag = Poseidon(AUTHORITY_DOMAIN, spend_secret)
//! nullifier    = Poseidon(NULLIFIER_DOMAIN, Poseidon(spend_secret, note_identity))
//!
//! Public instances:
//! - row 0: expected authority tag;
//! - row 1: expected nullifier.
//!
//! The spend secret and note identity remain private advice witnesses.
//!
//! This is a research relation, not WAM's final nullifier encoding. In
//! particular, spend_secret is currently a Pasta field element rather than
//! a fully constrained production key/scalar, and note_identity is expected
//! to be bound to the anchored note by a later integrated circuit.

use halo2_gadgets::poseidon::{
    primitives::{ConstantLength, Hash as PrimitiveHash, P128Pow5T3},
    Hash as PoseidonHash, Pow5Chip, Pow5Config,
};
use halo2_proofs::{
    circuit::{AssignedCell, Layouter, SimpleFloorPlanner, Value},
    pasta::Fp,
    plonk::{Advice, Circuit, Column, ConstraintSystem, Error, Fixed, Instance},
};

const WIDTH: usize = 3;
const RATE: usize = 2;
const HASH_INPUTS: usize = 2;

pub const AUTHORITY_DOMAIN: u64 = 0x5741_4d41;
pub const NULLIFIER_DOMAIN: u64 = 0x5741_4d4e;

#[derive(Clone, Debug)]
pub struct NullifierConfig {
    witness: Column<Advice>,
    instance: Column<Instance>,
    poseidon: Pow5Config<Fp, WIDTH, RATE>,
}

#[derive(Clone, Debug, Default)]
pub struct NullifierCircuit {
    pub spend_secret: Fp,
    pub note_identity: Fp,
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

impl NullifierCircuit {
    pub fn public_inputs(&self) -> Vec<Fp> {
        vec![
            authority_tag(self.spend_secret),
            nullifier(self.spend_secret, self.note_identity),
        ]
    }
}

fn hash_cells(
    config: &NullifierConfig,
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

impl Circuit<Fp> for NullifierCircuit {
    type Config = NullifierConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let witness = meta.advice_column();
        let instance = meta.instance_column();
        meta.enable_equality(witness);
        meta.enable_equality(instance);

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

        let poseidon =
            Pow5Chip::configure::<P128Pow5T3>(meta, state, partial_sbox, rc_a, rc_b);

        NullifierConfig {
            witness,
            instance,
            poseidon,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        let (secret, note_id, authority_domain, nullifier_domain) =
            layouter.assign_region(
                || "load nullifier witnesses",
                |mut region| {
                    let secret = region.assign_advice(
                        || "private spend authority",
                        config.witness,
                        0,
                        || Value::known(self.spend_secret),
                    )?;
                    let note_id = region.assign_advice(
                        || "private note identity",
                        config.witness,
                        1,
                        || Value::known(self.note_identity),
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

                    Ok((secret, note_id, authority_domain, nullifier_domain))
                },
            )?;

        let tag = hash_cells(
            &config,
            &mut layouter,
            authority_domain,
            secret.clone(),
            "authority tag",
        )?;
        layouter.constrain_instance(tag.cell(), config.instance, 0)?;

        let note_key = hash_cells(
            &config,
            &mut layouter,
            secret,
            note_id,
            "note-bound secret",
        )?;
        let nf = hash_cells(
            &config,
            &mut layouter,
            nullifier_domain,
            note_key,
            "nullifier",
        )?;
        layouter.constrain_instance(nf.cell(), config.instance, 1)
    }
}
