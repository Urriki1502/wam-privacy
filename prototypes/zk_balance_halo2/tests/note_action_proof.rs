use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{create_proof, keygen_pk, keygen_vk, verify_proof, SingleVerifier},
    poly::commitment::Params,
    transcript::{Blake2bRead, Blake2bWrite, Challenge255},
};
use rand_core::OsRng;
use wam_privacy_halo2_prototype::note_action::NoteActionCircuit;

const K: u32 = 14;

fn verify(
    params: &Params<EqAffine>,
    pk: &halo2_proofs::plonk::ProvingKey<EqAffine>,
    proof: &[u8],
    public: &[Fp],
) -> bool {
    let instance_columns: &[&[Fp]] = &[public];
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
fn note_derived_action_real_proof_binds_root_authority_and_nullifier() {
    let circuit = NoteActionCircuit {
        value: 125_000,
        recipient_tag: Fp::from(0x1111),
        spend_secret: Fp::from(0x2222),
        rho: Fp::from(0x3333),
        rseed: Fp::from(0x4444),
        siblings: [Fp::from(201), Fp::from(202), Fp::from(203), Fp::from(204)],
        directions: [false, true, false, true],
    };
    let public = circuit.public_inputs();

    let params: Params<EqAffine> = Params::new(K);
    let vk = keygen_vk(&params, &circuit).expect("verification key generation");
    let pk = keygen_pk(&params, vk, &circuit).expect("proving key generation");

    let instance_columns: &[&[Fp]] = &[&public];
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

    assert!(verify(&params, &pk, &proof, &public));

    for index in 0..3 {
        let mut tampered = public.clone();
        tampered[index] += Fp::from(1);
        assert!(!verify(&params, &pk, &proof, &tampered));
    }
}
