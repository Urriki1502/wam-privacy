use halo2_proofs::{
    pasta::{EqAffine, Fp},
    plonk::{create_proof, keygen_pk, keygen_vk},
    poly::commitment::Params,
    transcript::{Blake2bWrite, Challenge255},
};
use rand_core::OsRng;
use wam_privacy_halo2_prototype::{
    context::{NetworkId, ProofContext},
    hardened_bundle::{HardenedBundleCircuit, HardenedBundleInput, HardenedBundleOutput},
    note_action::authority_tag,
    serialization_v2::{
        verify_hardened_bundle_envelope, vk_identifier, HardenedBundleEnvelope,
        HardenedEnvelopeError, PUBLIC_INPUT_COUNT,
    },
};

const K: u32 = 15;

fn fixture() -> (HardenedBundleCircuit, ProofContext) {
    let fee = 3_000;
    let transparent_in = 10_000;
    let transparent_out = 2_000;
    let context = ProofContext::new(
        NetworkId::Regtest,
        [0xA5; 32],
        transparent_in,
        transparent_out,
        fee,
    );
    let mut circuit = HardenedBundleCircuit {
        inputs: [
            HardenedBundleInput {
                value: 50_000,
                recipient_tag: Fp::from(0x1111),
                spend_secret: Fp::from(0x2222),
                rho: Fp::from(0x3333),
                rseed: Fp::from(0x4444),
                siblings: [Fp::zero(); 4],
                directions: [false; 4],
            },
            HardenedBundleInput {
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
            HardenedBundleOutput {
                value: 52_500,
                recipient_tag: Fp::from(0x5555),
                spend_authority_tag: authority_tag(Fp::from(0x6666)),
                rho: Fp::from(0x7777),
                rseed: Fp::from(0x8888),
            },
            HardenedBundleOutput {
                value: 52_500,
                recipient_tag: Fp::from(0x5959),
                spend_authority_tag: authority_tag(Fp::from(0x6969)),
                rho: Fp::from(0x7979),
                rseed: Fp::from(0x8989),
            },
        ],
        fee,
        transparent_in,
        transparent_out,
        context_digest: context.digest(),
    };
    let id0 = circuit.inputs[0].identity();
    let id1 = circuit.inputs[1].identity();
    let upper = [Fp::from(701), Fp::from(702), Fp::from(703)];
    circuit.inputs[0].siblings = [id1, upper[0], upper[1], upper[2]];
    circuit.inputs[0].directions = [false, false, true, false];
    circuit.inputs[1].siblings = [id0, upper[0], upper[1], upper[2]];
    circuit.inputs[1].directions = [true, false, true, false];
    (circuit, context)
}

#[test]
fn real_proof_is_bound_to_vk_network_transaction_and_value_context() {
    let (circuit, context) = fixture();
    let public = circuit.public_inputs();
    let public_array: [Fp; PUBLIC_INPUT_COUNT] =
        public.clone().try_into().expect("nine public instances");

    let params: Params<EqAffine> = Params::new(K);
    let vk = keygen_vk(&params, &circuit).expect("verification key generation");
    let vk_again = keygen_vk(&params, &circuit).expect("repeat verification key generation");
    assert_eq!(vk_identifier(&vk), vk_identifier(&vk_again));

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

    let envelope =
        HardenedBundleEnvelope::new(pk.get_vk(), public_array, proof).expect("valid envelope");
    let encoded = envelope.encode().expect("encode");
    assert_eq!(
        verify_hardened_bundle_envelope(&params, pk.get_vk(), &context, &encoded),
        Ok(())
    );

    let mut wrong_network = context.clone();
    wrong_network.network = NetworkId::Testnet;
    assert_eq!(
        verify_hardened_bundle_envelope(&params, pk.get_vk(), &wrong_network, &encoded),
        Err(HardenedEnvelopeError::ContextMismatch)
    );

    let mut wrong_tx = context.clone();
    wrong_tx.transaction_digest[0] ^= 1;
    assert_eq!(
        verify_hardened_bundle_envelope(&params, pk.get_vk(), &wrong_tx, &encoded),
        Err(HardenedEnvelopeError::ContextMismatch)
    );

    let mut wrong_balance = context.clone();
    wrong_balance.transparent_in += 1;
    assert_eq!(
        verify_hardened_bundle_envelope(&params, pk.get_vk(), &wrong_balance, &encoded),
        Err(HardenedEnvelopeError::ContextMismatch)
    );

    let mut tampered = HardenedBundleEnvelope::decode(&encoded).expect("decode");
    tampered.public_inputs[1] += Fp::from(1);
    let tampered = tampered.encode().expect("encode tampered");
    assert_eq!(
        verify_hardened_bundle_envelope(&params, pk.get_vk(), &context, &tampered),
        Err(HardenedEnvelopeError::ProofRejected)
    );

    let mut bad_vk = encoded.clone();
    bad_vk[8] ^= 1;
    assert_eq!(
        verify_hardened_bundle_envelope(&params, pk.get_vk(), &context, &bad_vk),
        Err(HardenedEnvelopeError::VkIdMismatch)
    );
}
