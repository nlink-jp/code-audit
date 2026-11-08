# code-audit

自分たちのコードのリポジトリ 1 つを対象に、実際に信頼境界を越える脆弱性を
見つけ、どこまで見たかを台帳で示す Claude Code Skill。設計は
[RFP](docs/ja/code-audit-rfp.ja.md)（英訳: [RFP (en)](docs/en/code-audit-rfp.md)）。

> **状態: 作成中 — Phase 1 は完了、未リリース。** 簿記のスクリプト、
> データ契約、狩りクラス、6 段の SKILL.md が両プロファイルについて揃い、
> 見本リポジトリでのテストがあります。Phase 3 は完了: 実リポジトリ 2 つでの
> 通し実行 4 走（費用を記録、`docs/{ja,en}/reviews/`）と、実装に対する独立検証
> パス 2 巡。v0.1.0 までに残るのは第 4 走の学びの区切りとリリースです。

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
エージェントが防ぐ層を再構成してから判定する反証型の検証、置換の規則つきの
独立再検証（`standard`。再検証者の置換は、レコードを維持または弱めるものは
そのまま適用し、判定・深刻度・confidence・根拠種別を強めるものは
`findings.py add` が拒み、別の新しい検証者が確認したときだけ適用する）、
そして報告書の導出です。`--prior <run-dir>` を与えると、引用元が変わって
いない前回の `confirmed` / `needs_validation` を先に再検証し、前回の
`rejected` は同じ主張の再報告だけを抑え（単位は狩る）、各単位に前回の
結論を持たせます。

狩りクラス（`code-audit/classes/`）: 全リポジトリ向けの `generic.md` と、
製品型ごとの `mcp-server.md`・`cli.md`・`agent-runtime.md`。各クラスは
教訓の記録場所を出典に持ちます。組織の knowledge の見出し、組織の ADR、
そして自組織にナレッジの薄い汎用分野については、設計の由来である
スキル（origin）の該当ブロックを自分たちの言葉で書き直したもの。
`classes.py check-knowledge --knowledge <dir> [--adr <dir>] [--origin <dir>]`
が全出典をチェックアウトに対して検査します。

スクリプトが守るもの（手順が守らなくてよいもの）: 利用者の承認を
`run.py approve` で記録するまで、また批評者と検証者の予備枠を割り込むときは、
ハンターを割り当てられない。findings には台帳が持つ主張のレコードしか入らず、
両方の validate が相互に照合する。走らなかったテストのログは根拠にならない。
場所は名前ではなく identity で比べる。報告書に出る値はすべて先に無害化する。
初回の E2E（`docs/ja/reviews/2026-11-08-e2e-smoke-webhook-relay.ja.md`）から:
記帳済みの起動は再依頼と宣言したときだけ再記帳できる（`run.py count --rerun`）。
同根の候補は検証者を費やす前に統合する（`ledger.py merge-candidates`）。
批評者・検証者への入力は台帳から印字する（`ledger.py brief`）ので
coverage_id を打ち直さない。ツールチェーンのキャッシュは run 配下に置き、
ダウンロードは切る（`run.py exec`）。見積もりはハンターの束ねと再依頼を数える。
`lead` ノートは次走の `seed --prior` が批評者に渡す。第 2 走
（`docs/ja/reviews/2026-11-08-e2e-standard-webhook-relay.ja.md`）から:
全役の入力を台帳から印字する（`ledger.py brief hunter|critic|verifier|reverifier`）。
別プロファイルの前回実行も surface×boundary×class で突き合わせて持ち越す。第 3 走
（`docs/ja/reviews/2026-11-08-e2e-quick-web-fetch.ja.md`）から: 偵察の総合
`architecture.md` は保存した偵察返答からスクリプトが組み（`ledger.py architecture`）、
無ければどの役の brief も印字しない。brief は候補の判定案と根本原因、判定ごとの必須欄を
運ぶ。壊れた JSON は失敗位置と前後を添えて拒む。見積もりは起動済みの批評者を引き、
狩りが終われば待ち行列の実数を使い、候補率はプロファイル別。
残余リスクは RFP に記載: 対象自身のテストはサンドボックスなしに利用者の権限で
走る。サブエージェントに本当にシェルが無いかは、ランタイムが提供する
エージェント種別に依る。

## 開発

```
make check      # 構造検証 + スクリプトの挙動テスト
make package    # dist/code-audit-vX.Y.Z.zip（zip ルート = スキルフォルダ）
```

同梱スクリプトは標準ライブラリだけの Python 3.9 以上です（各 `--help`）。
`run.py`（実行メタデータ・承認・対象の既存テストの有界実行）、`ledger.py`
（網羅台帳と候補の待ち行列）、`findings.py`（所見レコード・digest・覚え書き）、
`compile.py`（報告書）、`classes.py`（狩りクラスの検査）。貢献者と
エージェント向けの規則は [`CLAUDE.md`](CLAUDE.md) と [`AGENTS.md`](AGENTS.md)。

## 謝辞

ワークフローの設計は
[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill)
（MIT）に由来します。コードや原文のままの文章は含めず、組織の規約のもとで
再実装しました。汎用の狩りクラスは、その攻撃クラスの観点を自分たちの言葉で
書き直し、由来のブロックを `origin:` 出典として引いています。
[`LICENSE`](LICENSE) の第三者表記を参照してください。

## ライセンス

MIT — [`LICENSE`](LICENSE) を参照。
