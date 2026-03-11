# Obsidian Vault Setup For Memory Ingest

This is the recommended setup for your environment:

- **MacBook** = primary working vault
- **iPhone** = synced editing/reading via Obsidian Sync
- **VM** = local synced mirror for ingest and future watcher automation

## Best Current Approach

Use:

1. **Obsidian Sync** between laptop and phone
2. **Obsidian Headless** on the VM to maintain a local synced copy
3. the VM-local copy as the source path for the ingest workflow

This is better than manually exporting the vault to the VM because:

- it uses the official Obsidian sync stack end to end
- the VM gets a normal local folder
- it avoids layering a second sync tool directly onto the live laptop vault
- it future-proofs the n8n ingest path

## Important Rule

Do **not** use both Obsidian desktop sync and Obsidian Headless on the **same
device**.

In this setup:

- MacBook uses normal Obsidian desktop/mobile sync
- iPhone uses normal Obsidian mobile sync
- VM uses only Obsidian Headless

That is the safe split.

## Target Paths

Use these paths unless you have a strong reason not to.

### On Your Mac

- primary vault:
  - `/Users/sgkmeyer/vaults/second-brain`

### On The VM

- synced ingest mirror:
  - `/home/ubuntu/obsidian-vault`

## Step 1: Create The Primary Vault On Your Mac

On your Mac:

1. Open Obsidian.
2. Create a new vault named something like `second-brain`.
3. Store it at:

```text
/Users/sgkmeyer/vaults/second-brain
```

Keep it as a normal local folder.

Do **not** put the live primary vault inside:

- iCloud Drive
- Dropbox
- OneDrive
- another third-party sync folder

## Step 2: Connect Your Phone To The Same Vault

Recommended approach: use **Obsidian Sync** for your Mac and phone.

On the Mac:

1. Open **Settings**.
2. Log in to your Obsidian account.
3. Enable the **Sync** core plugin.
4. Create a remote vault.
5. Connect your local vault to that remote vault.
6. Wait until the Mac shows fully synced.

On the iPhone:

1. Open Obsidian.
2. Choose **Setup Obsidian Sync**.
3. Log in to the same account.
4. Connect to the same remote vault.
5. Create the local mobile copy.
6. Wait until sync completes.

At this point:

- Mac and phone are your authoring devices
- the VM is still not involved yet

## Step 3: Create A Clean Vault Structure

Inside the vault, create the folders you want memory ingest to care about.

Recommended starting structure:

```text
Daily/
People/
Projects/
Coaching/
Reference/
Templates/
Attachments/
```

Recommended ingest targets at first:

- `Daily/`
- `People/`
- `Projects/`
- `Coaching/`
- optionally `Reference/`

Recommended to exclude conceptually from memory ingest:

- `.obsidian/`
- `Templates/`
- `Attachments/`

## Step 4: Prepare The VM

SSH to the VM:

```bash
ssh satoic-production
```

Create the local mirror folder:

```bash
mkdir -p /home/ubuntu/obsidian-vault
```

## Step 5: Install Obsidian Headless On The VM

On the VM:

```bash
npm install -g obsidian-headless
```

If `npm` is not available on the VM, install Node.js first.

## Step 6: Log In On The VM

On the VM:

```bash
ob login
```

Follow the login flow.

Then list available remote vaults:

```bash
ob sync-list-remote
```

You should see the same remote vault you created from the Mac.

## Step 7: Connect The VM Mirror To The Remote Vault

On the VM:

```bash
cd /home/ubuntu/obsidian-vault
ob sync-setup --vault "second-brain" --device-name vm-ingest
```

Replace `"second-brain"` with the actual remote vault name if it differs.

## Step 8: Pull The First Full Sync

On the VM:

```bash
cd /home/ubuntu/obsidian-vault
ob sync
```

After the first sync, verify files exist:

```bash
find /home/ubuntu/obsidian-vault -maxdepth 2 -type f | sort | sed -n '1,50p'
```

You should see your `.md` files locally on the VM.

## Step 9: Use The VM Path As The Ingest Source

This is the important handoff:

- your authoring path is the Mac/phone vault
- your ingest path is the VM-local mirror at:

```text
/home/ubuntu/obsidian-vault
```

Future watcher automation should watch this VM path, not your laptop path.

## Step 10: Test A Single Note Ingest

Once the note exists on the VM mirror, test one file manually.

Example:

```bash
ssh satoic-production '
  cd /home/ubuntu/ai-automation-stack &&
  scripts/memory-webhook.sh document \
    --source-ref Daily/2026-03-11.md \
    --file /home/ubuntu/obsidian-vault/Daily/2026-03-11.md \
    --tags daily-note
'
```

Expected result:

- first run -> `created`
- second run without edits -> `unchanged`
- after editing the note and syncing again -> `updated`

## Step 11: Decide How Fresh The VM Mirror Needs To Be

You have two good operating modes.

### Mode A: Simple / Manual

Before ingest work, run:

```bash
ssh satoic-production 'cd /home/ubuntu/obsidian-vault && ob sync'
```

This is the easiest starting point.

### Mode B: Always Fresh

Run continuous sync on the VM:

```bash
cd /home/ubuntu/obsidian-vault
ob sync --continuous
```

Later, this can be wrapped in a service if you want it always running.

My recommendation:

- start with **Mode A**
- move to **Mode B** only when you want near-real-time ingest

## Step 12: Stable Identity Rule

For memory ingest, note identity should be:

- `source = obsidian`
- `source_ref = vault-relative path`

Examples:

- `Daily/2026-03-11.md`
- `People/Dana Stripe.md`
- `Coaching/2026-Q1-reflection.md`

That matters because updates to the same file path become:

- `created`
- `unchanged`
- `updated`

instead of duplicate note memories.

## Recommended Daily Use

Use this pattern:

1. Write notes on Mac or phone.
2. Obsidian Sync keeps those authoring devices aligned.
3. Run `ob sync` on the VM when you want the latest notes available for ingest.
4. Ingest manually now, automate later.

## Fallback Option If You Do Not Want Obsidian Sync

If you do not want an Obsidian Sync subscription, the fallback is:

- keep the live vault on the Mac
- keep phone access however you prefer
- maintain a separate export mirror
- push that export mirror to the VM over Tailscale/SSH

That fallback is workable, but it is no longer my first recommendation.

## Why Tailscale Still Matters

With this setup, Tailscale is still useful for:

- SSH access to the VM
- triggering manual sync or ingest commands remotely
- future internal tooling between your devices and the VM

You do **not** need Tailscale as the primary file-sync layer if you use
Obsidian Sync + Obsidian Headless.

## Related Docs

- user guide: [memory-user-guide.md](/Users/sgkmeyer/ai-automation-stack/ops/memory-user-guide.md#L1)
- memory interfaces: [memory-external-interfaces.md](/Users/sgkmeyer/ai-automation-stack/ops/memory-external-interfaces.md#L1)

## Official References

- Obsidian Sync setup:
  https://help.obsidian.md/sync/setup
- Obsidian Sync settings / selective sync:
  https://help.obsidian.md/sync/settings
- Obsidian Headless:
  https://help.obsidian.md/sync/headless
- Avoid mixing Obsidian Sync with other sync solutions on the same vault:
  https://help.obsidian.md/sync/switch
- Tailscale SSH:
  https://tailscale.com/docs/features/tailscale-ssh
