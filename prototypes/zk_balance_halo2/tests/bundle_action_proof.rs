use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{create_proof, keygen_pk, keygen_vk, verify_proof, SingleVerifier},
    poly::commitment::Params,
    transcript::{Blake2bRead, Blake2bWrite, Challenge255},
};
use rand_core::OsRng;
use wam_privacy_halo2_prototype::{
    bundle_action::{BundleActionCircuit, BundleInput, BundleOutput},
    note_action::authority_tag,
};

const K: u32 = 15;

fn fixture() -> BundleActionCircuit {
    let mut circuit = BundleActionCircuit {
        inputs: [
            BundleInput {
                value: 50_000,
                recipient_tag: Fp::from(0x1111),
                spend_secret: Fp::from(0x2222),
                rho: Fp::from(0x3333),
                rseed: Fp::from(0x4444),
                siblings: [Fp::zero(); 4],
                directions: [false; 4],
            },
            BundleInput {
                value: 50_000,
                recipient_tag: Fp::from(0x1212),
                spend_secret: Fp::from(0x2323),
                rho: Fp::from(0x3434),
                rseed: Fp::from(0x4545),
                siblings: [Fp::zero(); 4],
                directions: [false; 4],
            },
        ],
        outputs: [
            BundleOutput {
                value: 47_500,
                recipient_tag: Fp::from(0x5555),
                spend_authority_tag: authority_tag(Fp::from(0x6666)),
                rho: Fp::from(0x7777),
                rseed: Fp::from(0x8888),
            },
            BundleOutput {
                value: 47_500,
                recipient_tag: Fp::from(0x5959),
                spend_authority_tag: authority_tag(Fp::from(0x6969)),
                rho: Fp::from(0x7979),
                rseed: Fp::from(0x8989),
            },
        ],
        fee: 5_000,
    };

    let id0 = circuit.inputs[0].identity();
    let id1 = circuit.inputs[1].identity();
    let upper = [Fp::from(701), Fp::from(702), Fp::from(703)];

    circuit.inputs[0].siblings = [id1, upper[0], upper[1], upper[2]];
    circuit.inputs[0].directions = [false, false, true, false];

    circuit.inputs[1].siblings = [id0, upper[0], upper[1], upper[2]];
    circuit.inputs[1].directions = [true, false, true, false];

    assert_eq!(circuit.inputs[0].root(), circuit.inputs[1].root());
    circuit
}

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
fn fixed_bundle_real_proof_binds_complete_public_relation() {
    let circuit = fixture();
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

    for index in 0..8 {
        let mut tampered = public.clone();
        tampered[index] += Fp::from(1);
        assert!(!verify(&params, &pk, &proof, &tampered));
    }
}
