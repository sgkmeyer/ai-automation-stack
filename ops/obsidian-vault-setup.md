# Obsidian Vault Setup For Memory Ingest

This is the current recommended setup for your environment:

- **MacBook** = primary working vault
- **iPhone** = optional reading/editing device however you prefer to manage it
- **VM** = `rsync` mirror used only for memory ingest

## Best Current Approach

Use:

1. your Mac vault as the source of truth
2. `rsync` over Tailscale/SSH to mirror that vault onto the VM
3. the VM-local mirror as the source path for memory ingest

This is the right first step because:

- it proves the ingest architecture without adding another subscription
- the VM still gets a normal local folder to ingest from
- it keeps the memory path independent from your day-to-day authoring setup
- it can later be replaced by a more automatic sync path if needed

## Future Upgrade Path

If you later buy Obsidian Sync, you can replace the `rsync` mirror with:

- Obsidian Sync on Mac/iPhone
- Obsidian Headless on the VM

That is a later improvement, not a requirement for proving the system now.

## Target Paths

Use these paths unless you have a strong reason not to.

### On Your Mac

- primary vault:
  - `/Users/sgkmeyer/vaults/second-brain`

### On The VM

- ingest mirror:
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

## Step 2: Decide What The Phone Does

For proving the memory system, the phone does not need to be part of the ingest
path yet.

The only hard requirement is:

- the Mac vault is the source of truth for the notes you want to ingest

If you also edit on the phone, make sure whatever process you use eventually
lands those edits back into the Mac vault before the next VM sync.

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

## Step 5: Run The First Mirror Sync

From your Mac, in this repo:

```bash
scripts/sync-obsidian-vault.sh --dry-run
```

If the preview looks sane, run the real sync:

```bash
scripts/sync-obsidian-vault.sh
```

Defaults:

- local vault: `/Users/sgkmeyer/vaults/second-brain`
- remote host: `satoic-production`
- remote path: `/home/ubuntu/obsidian-vault`

What the script does:

- mirrors the vault over SSH using `rsync`
- excludes `.obsidian/`, `.git/`, `.DS_Store`, and trash folders
- deletes removed files on the VM so the mirror stays accurate

Optional examples:

```bash
scripts/sync-obsidian-vault.sh --exclude Attachments/ --exclude Templates/
scripts/sync-obsidian-vault.sh --no-delete
```

## Step 6: Verify The Mirror On The VM

After the sync:

```bash
ssh satoic-production 'find /home/ubuntu/obsidian-vault -maxdepth 2 -type f | sort | sed -n "1,50p"'
```

You should see your `.md` files locally on the VM.

## Step 7: Use The VM Path As The Ingest Source

This is the important handoff:

- your authoring path is the Mac/phone vault
- your ingest path is the VM-local mirror at:

```text
/home/ubuntu/obsidian-vault
```

Future watcher automation should watch this VM path, not your laptop path.

## Step 8: Test A Single Note Ingest

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

## Step 9: Decide How Fresh The VM Mirror Needs To Be

You have two good operating modes.

### Mode A: Simple / Manual

Before ingest work, run:

```bash
scripts/sync-obsidian-vault.sh
```

This is the right starting point.

### Mode B: Scheduled

Later, add a scheduled `rsync` job from the Mac to the VM.

That gives you regular freshness without changing the architecture.

My recommendation:

- start with **Mode A**
- move to a scheduled sync only after manual ingest feels stable

## Step 10: Stable Identity Rule

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
2. Make sure the Mac vault contains the latest version you care about.
3. Run `scripts/sync-obsidian-vault.sh` when you want the latest notes on the VM.
4. Ingest manually now, automate later.

## Why Tailscale Still Matters

With this setup, Tailscale is useful for:

- SSH access to the VM
- carrying the `rsync` mirror traffic safely
- triggering manual sync or ingest commands remotely
- future internal tooling between your devices and the VM

## Related Docs

- user guide: [memory-user-guide.md](/Users/sgkmeyer/ai-automation-stack/ops/memory-user-guide.md#L1)
- memory interfaces: [memory-external-interfaces.md](/Users/sgkmeyer/ai-automation-stack/ops/memory-external-interfaces.md#L1)

## Later Upgrade Option

If you later buy Obsidian Sync, the VM mirror can be reworked to use:

- Obsidian Sync on the Mac and phone
- Obsidian Headless on the VM

For now, `rsync` is the simpler and cheaper proof path.

## References

- Tailscale SSH:
  https://tailscale.com/docs/features/tailscale-ssh
- `rsync` manual:
  https://download.samba.org/pub/rsync/rsync.1
