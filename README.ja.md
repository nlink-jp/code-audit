# code-audit

自分たちのコードのリポジトリ 1 つを対象に、実際に信頼境界を越える脆弱性を
見つけ、どこまで見たかを台帳で示す Claude Code Skill。設計は
[RFP](docs/ja/code-audit-rfp.ja.md)（英訳: [RFP (en)](docs/en/code-audit-rfp.md)）。

> **状態: 作成中。** 簿記のスクリプト、データ契約、狩りクラス、SKILL.md の
> 6 段の手順が揃い、`quick` プロファイルについてテスト済みです。`standard`
> の 2 波目以降・検証の第 2 段・`--prior` の持ち越しは次の区切りで、
> それまで SKILL.md は `quick` で走るよう案内します。v0.1.0 は両方を含みます。

**何をするか。** 親エージェントが隔離されたサブエージェントで 6 段を回します。
偵察、網羅台帳に基づく狩りの波、候補ごとに別の新しい検証者が反証を試みる
検証、3 値の判定を持つ schema 検証済みの `findings.json`（`confirmed` は
完全な trace と根拠を持ち深刻度つき、`needs_validation` は未解決の事実を
持ち深刻度なし、`rejected` は反証された主張で次回の再報告を抑える）、
最終レコードの独立再検証、そしてレコードから導出する日英の報告書です。
文章が判定を変えることはありません。

**組織版の特徴。** 簿記（網羅台帳・findings・実行メタデータ・費用見積もり・
報告書）は同梱の標準ライブラリだけの Python スクリプトが 1 件ずつ行い、
モデルは判断だけをします。狩りの分類は、組織が実際に出荷して knowledge に
記録した欠陥（MCP サーバ・CLI・LLM エージェントランタイム）から起こし、
汎用クラスと並べます。監査対象のリポジトリは敵対的入力として扱います。
サブエージェントは読み取り専用で、対象の既存テストを動かすのは親だけ、
それも偵察のコマンド台帳が許可したものに限ります。狩りに入る前に
エージェント呼び出し回数の見積もりを示し、承認を待ちます。

## インストール

[Releases](https://github.com/nlink-jp/code-audit/releases)（まだありません）
から `code-audit-vX.Y.Z.zip` を取得し、登録します。

- **アプリで**（Claude Desktop、claude.ai、モバイル）: スキル設定
  （カスタマイズ → スキル）から zip を追加します。この経路を推奨します。
  スキルの保存場所が変わっても壊れません。
- **Claude Code**: `unzip code-audit-vX.Y.Z.zip -d ~/.claude/skills/`、
  またはプロジェクトの `.claude/skills/` に展開してプロジェクト限定で使います。

チェックアウトからは:

```bash
make install
```

リリース zip を作ってそれを展開するので、動かすものはリリースが出荷する
ものと同じです。`make install DEST=/path/to/skills` で別の場所へ、
`make uninstall` で削除します。

## 使い方（予定）

```
/code-audit <target-dir> [--output <dir>] [--profile quick|standard]
            [--budget <N>] [--prior <run-dir>]... [--knowledge <dir>]
```

フル監査は Claude Code でだけ動きます（Agent ツールが要ります）。claude.ai
のチャット面ではガイダンスモードで答えます。成果物は利用者が指定する
ディレクトリに書き、既定は `~/code-audit-runs/<repo>/run-<N>` で、対象の
内側には書きません。成果物の構成と実行境界は RFP を参照してください。

6 段の内容: 読み取り専用の 4 役による偵察（製品と実行可能なコマンド、主体と
守り、入口とシンク、既存テストと配備でしか分からないこと）。ここでコマンド
台帳を書き、許可したテストを 1 度だけ走らせます。次に費用ゲートで
エージェント呼び出し回数の見込みを示して承認を待ちます。台帳の単位ごとの
狩り（ハンターは自分の単位のクラスだけを読む）、候補ごとに別の新しい
エージェントが防ぐ層を再構成してから判定する反証型の検証、独立再検証
（`standard`）、そして報告書の導出です。

狩りクラス（`code-audit/classes/`）: 全リポジトリ向けの `generic.md` と、
製品型ごとの `mcp-server.md`・`cli.md`・`agent-runtime.md`。各クラスは
組織が教訓を記録した場所（knowledge の見出し、または ADR）を出典に持ち、
`classes.py check-knowledge --knowledge <dir> [--adr <dir>]` がチェックアウト
に対して出典を検査します。

## 開発

```
make check      # 構造検証 + スクリプトの挙動テスト
make package    # dist/code-audit-vX.Y.Z.zip（zip ルート = スキルフォルダ）
```

同梱スクリプトは標準ライブラリだけの Python 3.9 以上です（各 `--help`）。
`run.py`（実行メタデータと対象の既存テストの有界実行）、`ledger.py`
（網羅台帳と候補の待ち行列）、`findings.py`（所見レコードと覚え書き）、
`compile.py`（報告書）、`classes.py`（狩りクラスの検査）。貢献者と
エージェント向けの規則は [`CLAUDE.md`](CLAUDE.md) と [`AGENTS.md`](AGENTS.md)。

## 謝辞

ワークフローの設計は
[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill)
（MIT）に由来します。コードや文章は含めず、組織の規約のもとで再実装
しました。[`LICENSE`](LICENSE) の第三者表記を参照してください。

## ライセンス

MIT — [`LICENSE`](LICENSE) を参照。
