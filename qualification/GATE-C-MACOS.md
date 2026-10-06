# Gate C — macOS Current-Core Requalification

Gate C is the runtime compatibility gate for the pinned WSP implementation against the pinned current WAM Core daemon.

## Pins

- WSP: `a8522fee9b6eda285998a5ff4a45d6bc4eb991b3`
- WAM Core: `260bc468e5adffea7ce68d8f97fac3e27e4c50b2`

## Why macOS has a separate runner

The full historical WSP qualification script includes Atheris/libFuzzer. Atheris is intentionally pinned only on Linux in the WSP development requirements.

Running the unmodified full qualification on macOS would therefore mix a platform/tooling limitation into the current-Core compatibility question.

Gate C on macOS instead runs:

- WSP internal self-test;
- black-box contract conformance;
- 10,000-case independent differential testing;
- current-Core two-node isolated regtest E2E;
- PSBT/Core interop;
- current-Core regtest suite;
- real reorg depths exercised by the existing real-node suite.

Coverage-guided fuzz evidence remains a separate Linux qualification artifact.

## Safety boundary

The Gate C runtime tests use synthetic keys, private temporary datadirs, loopback RPC and isolated regtest. They do not attach to an existing user wallet and do not target public pool or third-party infrastructure.

## Apple Silicon build note

The WAM source fetch step currently creates a RandomX build before the macOS-specific build script runs. To avoid inheriting an x86-oriented intermediate build on Apple Silicon, the bootstrap removes only the generated RandomX build directory after source preparation. `build_macos.sh` then rebuilds RandomX using its ARM-aware path.

No WAM source file is modified by this workaround.

## Entry point

From a checkout of `wam-privacy`:

```bash
bash scripts/bootstrap_phase1_macos.sh
```

After a successful build the script writes a private environment file under:

```
~/wam-phase1-gate-c/gate-c-env.sh
```

Then run:

```bash
source ~/wam-phase1-gate-c/gate-c-env.sh
bash scripts/run_phase1_macos_gate_c.sh
```

The final evidence file is written under the pinned WSP checkout at:

```
~/wam-phase1-gate-c/wam-silent-payments/reports/phase1-macos/gate-c-evidence.json
```
