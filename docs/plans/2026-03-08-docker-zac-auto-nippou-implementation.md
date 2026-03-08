# Docker化 zac_auto_nippou Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** zac_auto_nippouスクリプトをDockerコンテナで実行できるようにする。

**Architecture:** entrypoint.shでgenerate_auth.pyとmain.pyを順次実行。既存のDockerfileとdocker-compose.ymlを修正し、.envとconfig.jsonをボリュームマウントする。auth.jsonはコンテナ内で生成。

**Tech Stack:** Docker, Docker Compose, Bash, Python 3.12, uv, Playwright

---

## Task 1: Create entrypoint.sh

**Files:**
- Create: `docker/zac_auto_nippou/entrypoint.sh`

**Step 1: Create entrypoint.sh with sequential execution logic**

Create the file with the following content:

```bash
#!/bin/bash
set -e  # エラーが発生したら即座に終了

echo "=== ZAC Auto Nippou Docker ==="
echo "Step 1: Generating authentication..."
uv run python generate_auth.py

if [ $? -eq 0 ]; then
    echo "Step 1: Authentication completed successfully"
    echo ""
    echo "Step 2: Running main automation..."
    uv run python main.py

    if [ $? -eq 0 ]; then
        echo "Step 2: Automation completed successfully"
        echo "=== All tasks completed ==="
    else
        echo "ERROR: main.py failed"
        exit 1
    fi
else
    echo "ERROR: generate_auth.py failed"
    exit 1
fi
```

**Step 2: Verify file was created**

Run:
```bash
ls -la docker/zac_auto_nippou/entrypoint.sh
cat docker/zac_auto_nippou/entrypoint.sh
```

Expected: File exists with correct content

**Step 3: Commit entrypoint.sh**

```bash
git add docker/zac_auto_nippou/entrypoint.sh
git commit -m "feat: add entrypoint.sh for Docker sequential execution

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Fix Dockerfile COPY paths

**Files:**
- Modify: `docker/zac_auto_nippou/Dockerfile:16-20`

**Step 1: Fix pyproject.toml and uv.lock COPY path**

Change line 16 from:
```dockerfile
COPY zac_auto_nippou/pyproject.toml zac_auto_nippou/uv.lock .
```

To:
```dockerfile
COPY zac_auto_nippou/pyproject.toml zac_auto_nippou/uv.lock /app/
```

**Step 2: Verify syntax**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose config
```

Expected: No syntax errors in docker-compose.yml

**Step 3: Commit COPY path fix**

```bash
git add docker/zac_auto_nippou/Dockerfile
git commit -m "fix: correct COPY paths in Dockerfile

Build context is task-automation root, so use correct paths

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Add entrypoint.sh to Dockerfile

**Files:**
- Modify: `docker/zac_auto_nippou/Dockerfile` (after line 25)

**Step 1: Add COPY and chmod for entrypoint.sh**

After line 25 (after `RUN uv run playwright install-deps chromium`), add:

```dockerfile
# Copy and set permissions for entrypoint script
COPY docker/zac_auto_nippou/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
```

**Step 2: Verify Dockerfile syntax**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose config
```

Expected: No errors

**Step 3: Commit entrypoint.sh integration**

```bash
git add docker/zac_auto_nippou/Dockerfile
git commit -m "feat: add entrypoint.sh to Docker image

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Update Dockerfile CMD

**Files:**
- Modify: `docker/zac_auto_nippou/Dockerfile:28`

**Step 1: Change CMD to use entrypoint.sh**

Change line 28 from:
```dockerfile
CMD ["uv", "run", "python", "main.py"]
```

To:
```dockerfile
CMD ["/app/entrypoint.sh"]
```

**Step 2: Verify Dockerfile syntax**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose config
```

Expected: No errors

**Step 3: Commit CMD change**

```bash
git add docker/zac_auto_nippou/Dockerfile
git commit -m "refactor: use entrypoint.sh as CMD

Execute both generate_auth.py and main.py sequentially

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update docker-compose.yml volumes

**Files:**
- Modify: `docker/zac_auto_nippou/docker-compose.yml:9-11`

**Step 1: Replace volumes configuration**

Change lines 9-11 from:
```yaml
    volumes:
      - ../../zac_auto_nippou/config.json:/app/config.json
      - ../../zac_auto_nippou/auth.json:/app/auth.json
```

To:
```yaml
    volumes:
      - ../../zac_auto_nippou/config.json:/app/config.json:ro
      - ../../zac_auto_nippou/.env:/app/.env:ro
```

**Step 2: Verify docker-compose syntax**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose config
```

Expected: Valid YAML with correct volumes configuration

**Step 3: Commit volumes update**

```bash
git add docker/zac_auto_nippou/docker-compose.yml
git commit -m "refactor: update volumes to mount .env instead of auth.json

Mount .env for credentials, remove auth.json (generated in container)
Add :ro flag for read-only mounts

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Build Docker image

**Files:**
- Test: Build process

**Step 1: Build the Docker image**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose build
```

Expected: Build succeeds with no errors
- All COPY commands succeed
- uv sync installs dependencies
- Playwright installs chromium and deps
- entrypoint.sh has execute permissions

**Step 2: Verify image was created**

Run:
```bash
docker images | grep zac
```

Expected: zac_auto_nippou image appears in list

**Step 3: Document successful build**

No commit needed (verification only)

---

## Task 7: Test with missing .env (error case)

**Files:**
- Test: Error handling

**Step 1: Temporarily rename .env file**

Run:
```bash
cd /workspaces/task-automation
mv zac_auto_nippou/.env zac_auto_nippou/.env.backup 2>/dev/null || echo ".env already missing"
```

**Step 2: Run container and verify error handling**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose up
```

Expected:
- Container starts
- Prints: "Step 1: Generating authentication..."
- Prints: "エラー: .envファイルにZAC_IDとZAC_PASSWORDを設定してください。"
- Prints: "ERROR: generate_auth.py failed"
- Container exits with error

**Step 3: Restore .env file**

Run:
```bash
cd /workspaces/task-automation
mv zac_auto_nippou/.env.backup zac_auto_nippou/.env 2>/dev/null || echo ".env already exists"
```

**Step 4: Document error handling test**

No commit needed (verification only)

---

## Task 8: Test with valid configuration (success case)

**Files:**
- Test: Successful execution

**Step 1: Verify required files exist**

Run:
```bash
cd /workspaces/task-automation
ls zac_auto_nippou/.env
ls zac_auto_nippou/config.json
```

Expected: Both files exist

**Step 2: Run container with valid configuration**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose up
```

Expected output:
```
=== ZAC Auto Nippou Docker ===
Step 1: Generating authentication...
ZACのログイン画面を開きます...
[authentication process]
Step 1: Authentication completed successfully

Step 2: Running main automation...
カレンダーと配分を計算しました: 2026年3月
[automation process]
Step 2: Automation completed successfully
=== All tasks completed ===
```

**Step 3: Verify container exited cleanly**

Run:
```bash
docker ps -a | grep zac_auto_nippou_app | head -1
```

Expected: Container shows "Exited (0)" status

**Step 4: Document successful execution**

No commit needed (verification only)

---

## Task 9: Test read-only volume mounts

**Files:**
- Test: Security - read-only mounts

**Step 1: Verify volumes are mounted read-only**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose run --rm zac-automation sh -c "touch /app/config.json.test 2>&1 || echo 'Read-only mount working correctly'"
```

Expected: "Read-only file system" error or "Read-only mount working correctly"

**Step 2: Verify .env is also read-only**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose run --rm zac-automation sh -c "touch /app/.env.test 2>&1 || echo 'Read-only mount working correctly'"
```

Expected: "Read-only file system" error or "Read-only mount working correctly"

**Step 3: Document security test**

No commit needed (verification only)

---

## Task 10: Create usage documentation

**Files:**
- Modify: `zac_auto_nippou/README.md` (add Docker section)

**Step 1: Add Docker usage section to README**

After the existing "実行方法 (ローカル)" section, add:

```markdown

## 実行方法 (Docker)

### 1. 前提条件

環境変数ファイルと設定ファイルが準備されていることを確認してください。

```bash
ls zac_auto_nippou/.env        # ZAC_ID, ZAC_PASSWORD
ls zac_auto_nippou/config.json # target_year, target_month, etc.
```

### 2. Docker イメージのビルド

```bash
cd docker/zac_auto_nippou
docker-compose build
```

### 3. 実行

```bash
cd docker/zac_auto_nippou
docker-compose up
```

実行が完了すると、コンテナは自動的に終了します。

### 4. トラブルシューティング

**エラー: `.env`ファイルが見つからない**
- `zac_auto_nippou/.env`ファイルが存在することを確認してください
- `.env.sample`を参考に作成してください

**エラー: `config.json`が見つからない**
- `zac_auto_nippou/config.json`ファイルが存在することを確認してください
- `config.sample.json`を参考に作成してください

**認証エラー**
- `.env`ファイルのZAC_IDとZAC_PASSWORDが正しいことを確認してください
```

**Step 2: Verify README syntax**

Run:
```bash
cat zac_auto_nippou/README.md | grep -A 5 "実行方法 (Docker)"
```

Expected: New Docker section appears in README

**Step 3: Commit README update**

```bash
git add zac_auto_nippou/README.md
git commit -m "docs: add Docker usage instructions to README

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 11: Final verification and cleanup

**Files:**
- Review: All changes

**Step 1: Verify all files are committed**

Run:
```bash
cd /workspaces/task-automation
git status
```

Expected: Working tree clean

**Step 2: List all commits from this session**

Run:
```bash
git log --oneline --since="2026-03-08" | grep -i "docker\|entrypoint"
```

Expected: List of Docker-related commits

**Step 3: Run final end-to-end test**

Run:
```bash
cd docker/zac_auto_nippou
docker-compose down
docker-compose up
```

Expected: Complete successful execution

**Step 4: Document completion**

No commit needed (verification only)

---

## Completion Checklist

- [ ] entrypoint.sh created with sequential execution logic
- [ ] Dockerfile COPY paths fixed
- [ ] entrypoint.sh added to Docker image with execute permissions
- [ ] Dockerfile CMD updated to use entrypoint.sh
- [ ] docker-compose.yml volumes updated (.env mounted, auth.json removed, :ro flags)
- [ ] Docker image builds successfully
- [ ] Error handling tested (missing .env)
- [ ] Successful execution tested
- [ ] Read-only mounts verified
- [ ] README.md updated with Docker usage instructions
- [ ] All changes committed

## Success Criteria

1. ✅ `docker-compose build` succeeds without errors
2. ✅ `docker-compose up` executes both scripts sequentially
3. ✅ Container exits cleanly after completion
4. ✅ Error handling works correctly (missing .env fails gracefully)
5. ✅ Read-only mounts prevent file modification
6. ✅ Documentation complete and clear
7. ✅ All commits follow conventional commit format

## Notes

- auth.json is generated inside the container and not persisted
- This is intentional - authentication happens every run
- .env and config.json are mounted read-only for security
- Container exits automatically after execution (no daemon mode)
