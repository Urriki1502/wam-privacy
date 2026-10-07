use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{create_proof, keygen_pk, keygen_vk},
    poly::commitment::Params,
    transcript::{Blake2bWrite, Challenge255},
};
use rand_core::OsRng;
use wam_privacy_halo2_prototype::{
    bundle_action::{BundleActionCircuit, BundleInput, BundleOutput},
    note_action::authority_tag,
    serialization::{
        verify_bundle_envelope, BundleProofEnvelope, EnvelopeError, PUBLIC_INPUT_COUNT,
    },
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

#[test]
fn canonical_envelope_verifies_real_phase10b_proof() {
    let circuit = fixture();
    let public = circuit.public_inputs();
    let public_array: [Fp; PUBLIC_INPUT_COUNT] =
        public.clone().try_into().expect("eight public instances");

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

    let vk_id = [0x5A; 32];
    let envelope = BundleProofEnvelope::new(vk_id, public_array, proof).expect("valid envelope");
    let encoded = envelope.encode().expect("canonical encoding");

    assert_eq!(
        verify_bundle_envelope(&params, pk.get_vk(), vk_id, &encoded),
        Ok(())
    );

    let mut wrong_vk_id = vk_id;
    wrong_vk_id[0] ^= 1;
    assert_eq!(
        verify_bundle_envelope(&params, pk.get_vk(), wrong_vk_id, &encoded),
        Err(EnvelopeError::VkIdMismatch)
    );

    let mut tampered_public = BundleProofEnvelope::decode(&encoded).expect("decode");
    tampered_public.public_inputs[2] += Fp::from(1);
    let tampered_public = tampered_public.encode().expect("encode");
    assert_eq!(
        verify_bundle_envelope(&params, pk.get_vk(), vk_id, &tampered_public),
        Err(EnvelopeError::ProofRejected)
    );

    let mut tampered_proof = BundleProofEnvelope::decode(&encoded).expect("decode");
    let last = tampered_proof.proof.len() - 1;
    tampered_proof.proof[last] ^= 1;
    let tampered_proof = tampered_proof.encode().expect("encode");
    assert_eq!(
        verify_bundle_envelope(&params, pk.get_vk(), vk_id, &tampered_proof),
        Err(EnvelopeError::ProofRejected)
    );
}
