use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{
        create_proof, keygen_pk, keygen_vk, verify_proof, Circuit, SingleVerifier,
    },
    poly::commitment::Params,
    transcript::{Blake2bRead, Blake2bWrite, Challenge255},
};
use rand_core::OsRng;
use wam_privacy_halo2_prototype::{
    anchor::AnchorCircuit,
    nullifier::NullifierCircuit,
    BalanceCircuit,
};

fn prove<C: Circuit<Fp> + Clone>(
    k: u32,
    circuit: C,
    instance_columns: &[&[Fp]],
) -> (Params<EqAffine>, halo2_proofs::plonk::ProvingKey<EqAffine>, Vec<u8>) {
    let params: Params<EqAffine> = Params::new(k);
    let vk = keygen_vk(&params, &circuit).expect("verification key generation");
    let pk = keygen_pk(&params, vk, &circuit).expect("proving key generation");

    let mut transcript = Blake2bWrite::<_, EqAffine, Challenge255<_>>::init(vec![]);
    create_proof(
        &params,
        &pk,
        &[circuit],
        &[instance_columns],
        OsRng,
        &mut transcript,
    )
    .expect("proof creation");

    let proof = transcript.finalize();
    assert!(!proof.is_empty());
    (params, pk, proof)
}

fn verify(
    params: &Params<EqAffine>,
    pk: &halo2_proofs::plonk::ProvingKey<EqAffine>,
    proof: &[u8],
    instance_columns: &[&[Fp]],
) -> bool {
    let strategy = SingleVerifier::new(params);
    let mut transcript = Blake2bRead::<_, EqAffine, Challenge255<_>>::init(proof);
    verify_proof(
        params,
        pk.get_vk(),
        strategy,
        &[instance_columns],
        &mut transcript,
    )
    .is_ok()
}

#[test]
fn real_balance_proof_creates_and_verifies() {
    let circuit = BalanceCircuit {
        spent: 100_000,
        transparent_in: 0,
        created: 74_000,
        transparent_out: 25_000,
        fee: 1_000,
    };
    let instances: &[&[Fp]] = &[];

    let (params, pk, proof) = prove(11, circuit, instances);
    assert!(verify(&params, &pk, &proof, instances));
}

#[test]
fn real_anchor_proof_verifies_and_rejects_wrong_public_root() {
    let circuit = AnchorCircuit {
        leaf: Fp::from(101),
        siblings: [
            Fp::from(201),
            Fp::from(202),
            Fp::from(203),
            Fp::from(204),
        ],
        directions: [false, true, false, true],
    };
    let root = circuit.root();
    let public = [root];
    let instances: &[&[Fp]] = &[&public];

    let (params, pk, proof) = prove(12, circuit, instances);
    assert!(verify(&params, &pk, &proof, instances));

    let wrong_public = [root + Fp::from(1)];
    let wrong_instances: &[&[Fp]] = &[&wrong_public];
    assert!(!verify(&params, &pk, &proof, wrong_instances));
}

#[test]
fn real_nullifier_proof_verifies_and_rejects_wrong_public_nullifier() {
    let circuit = NullifierCircuit {
        spend_secret: Fp::from(0x1234_5678),
        note_identity: Fp::from(0x00ab_cdef),
    };
    let public = circuit.public_inputs();
    let instances: &[&[Fp]] = &[&public];

    let (params, pk, proof) = prove(10, circuit, instances);
    assert!(verify(&params, &pk, &proof, instances));

    let wrong_public = [public[0], public[1] + Fp::from(1)];
    let wrong_instances: &[&[Fp]] = &[&wrong_public];
    assert!(!verify(&params, &pk, &proof, wrong_instances));
}
