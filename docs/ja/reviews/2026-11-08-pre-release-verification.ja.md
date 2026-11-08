# リリース前独立検証（2026-11-08）— 指摘のトリアージ

対象: `a4be51a`（Phase 1 完了時点）。別コンテキストの検証者 3 本（設計整合と
モデル向け品質 / スクリプトの正しさと安全性 / 狩りクラスの出典忠実性）を
読み取り専用で走らせ、指摘を根本原因のクラスごとに分類した。判定は本人が行い、
自動では適用していない。V-1 と F-1 は本人が別環境で再現を確認した。

凡例: **採用** = 区切り (4) で直す / **文書** = コードではなく RFP・README に
残余として書く / **保留** = Phase 2 以降で判断 / **不採用** = 理由を記す。

## A. 制御が散文のまま（スクリプトが守っていない）

| # | 指摘 | 深刻度 | 判定 | 直し方 |
|---|------|--------|------|--------|
| A1 | 費用ゲートの承認と予算が `assign` に効かない。承認分岐で `set-budget` を呼ばず `budget: null` のまま `count` は超過を言わない | high | 採用 | `run.py approve RUN --budget N` を追加し、`assign` は未承認・予算超過（予備枠込み）を拒む |
| A2 | 候補の `source_digests` を親が埋める手段がスクリプトに無い。手で JSON を触る唯一の経路 | high | 採用 | `findings.py digest <record.json> --target` を追加（trace・evidence の file を埋めて書き戻す）。SKILL.md はそれを呼ぶだけ |
| A3 | サブエージェントを読み取り専用ツールだけで起動する指定が無い。汎用エージェントは Bash を持ち対象の `make test` を走らせられる | high | 採用＋保留 | SKILL.md の起動手順に「Read / Glob / Grep のみ、Bash・Write を持つ種別は使わない」を書く。サブエージェント定義の同梱は Skill の仕組みを確かめてから（保留） |
| A4 | `set-status complete` が未処理（planned / in_progress / pending 候補）を見ない | medium | 採用 | 残があれば拒む |
| A5 | agent id の run 内再利用を拒まない（`assign` は当該単位の attempts しか見ない） | low | 採用 | 台帳全体の使用済み id を集めて拒む |
| A6 | `count --n` が負値を検証なしに書く。`init --budget 0` が空ディレクトリを残す | low | 採用 | 書込前に検証、validate を mkdir の前へ |
| A7 | 走らなかった／timeout したコマンドのログも `existing_test` の根拠に使える（存在しか見ない） | medium | 採用 | `record_errors` が `checks/<id>.log` の先頭（exit_code / timed_out）を読み、走っていないログを拒む。SKILL.md Phase 1 に失敗時の扱いを書く |

## B. findings と台帳の整合を誰も検査していない

| # | 指摘 | 深刻度 | 判定 | 直し方 |
|---|------|--------|------|--------|
| B1 | 判定していない record・存在しない coverage_ids の record が `add` を通り、両 validate が緑のまま報告書に confirmed で載る（再現済） | high | 採用 | `add` は fingerprint が pending（`--replace` では decided）で coverage_ids が台帳に実在することを要求。`validate` は findings ⇄ decided ⇄ decisions を相互検査。`compile.py` は decided の record だけを所見表に出す |
| B2 | 持ち越し record の単位が `deferred`、または quick → standard で coverage_id が解決しないと `add` 済み・`decide` 不能の袋小路 | high | 採用 | `seed` は解決しない record を carried に入れず `unlinked_prior` に記録して報告へ。`decide --agent` は deferred 単位も受ける（検証者が所有者になり candidate へ） |
| B3 | `--replace` が未登録 fingerprint を黙って新規追加 | medium | 採用 | 既存が無ければ拒む |
| B4 | 置換で coverage_ids の変更が未検査 | medium | 採用 | 置換は fingerprint・coverage_ids 不変を要求 |
| B5 | 置換後の `decide` 忘れを validate が見ない | medium | 採用 | B1 の相互検査で捕まる |

## C. 場所を名前で比べている（knowledge「Compare places by identity」の自己違反）

| # | 指摘 | 深刻度 | 判定 | 直し方 |
|---|------|--------|------|--------|
| C1 | `is_inside` が大文字小文字・NFD の別綴りで迂回され、対象の中に出力先ができる（再現済） | high | 採用 | stat の identity（dev, ino）で祖先を遡る比較に置き換える |
| C2 | `digests_for` が対象内の symlink を辿って外を読む・外のツリーを歩く。上限なし | medium | 採用 | lstat で symlink は「missing」扱い、rglob から除外、総バイト・件数の上限 |
| C3 | `.git` ファイルの `gitdir:` が任意の場所を指し、他リポジトリの名前と HEAD が成果物に入る | low-medium | 採用 | gitdir は対象配下か worktree 構成のみ、他は `unversioned` |
| C4 | `--prior` の record を無検証で信用（絶対パスのキーを digest する、壊れた record で KeyError） | low-medium | 採用 | prior の record を `record_errors` に通し、不合格は warning で捨てる |
| C5 | `__pycache__` がディレクトリ digest に入り、exec 後に `changed_source` と誤判定しうる | low | 採用 | ディレクトリ digest から `__pycache__` / `*.pyc` / `.git` を除外 |

## D. 第三者テキストを出口で無害化していない（knowledge「Make third-party text inert … once」の自己違反）

| # | 指摘 | 深刻度 | 判定 | 直し方 |
|---|------|--------|------|--------|
| D1 | `plain()` が C0 / C1 / 双方向制御を通す。バッククォート内の値で脱出できる | medium | 採用 | Unicode カテゴリ C を除去、バッククォート内に置く値はバッククォートを拒む |
| D2 | `$` アンカーが末尾改行を許し、fingerprint / agent id / check_log が二重化する | medium | 採用 | `re.fullmatch`（`\Z`） |
| D3 | 対象の remote URL 由来の repo 名が無制限（ESC・空白・`..`）で題名と既定ディレクトリ名になる | medium | 採用 | 要素を `^[A-Za-z0-9._-]{1,100}$` の形で受け、外れたら basename |
| D4 | exec の stdout / stderr をログへ生で保存 | low | 文書 | ファイルへは verbatim（knowledge L1803）。README に「ログは `cat` せず読む」の注意 |

## E. 台帳の状態機械の穴

| # | 指摘 | 深刻度 | 判定 | 直し方 |
|---|------|--------|------|--------|
| E1 | 批評が `candidate` 単位を reassign すると `merge-critic` 全体が拒否される（candidates が宙に浮く） | medium | 採用 | 候補を抱える単位の reassign を明示的に拒み、批評契約に「candidate 単位は再割当せず `missing_units` で面を切り直す」と書く |
| E2 | `blocked` の出口が批評の reassign だけ | low | 採用 | `defer` が blocked も受ける（理由つき）。SKILL.md に blocked の扱い |
| E3 | 候補に `verdict` キーがあると `proposed_verdict` を黙って上書き | low | 採用 | 両方あれば拒む。契約に `proposed_verdict` を明記 |
| E4 | `seed` / `merge-critic` がクラス参照の実在を見ない（SKILL.md は「bad references を拒む」と言う） | medium | 採用 | `build_unit` が `classes/` の見出し一覧と照合 |
| E5 | 前回 rejected の抑止は `record` では効かない（hunter が再提案すると queue される） | medium | 採用 | `record` は suppressed と一致する候補を queue せず単位の note に残す |
| E6 | 候補の coverage_ids が fingerprint を主張した単位を含まなくてよい | low | 採用 | 含むことを要求 |
| E7 | `status` の `uncovered` が件数だけで、批評に渡す実体が無い | medium | 採用 | 実体を返す |

## F. SKILL.md の記述不足（親が手を止める箇所）

採用: F1 偵察 4 回の起動を事前に告げる / F2 hunter・verifier の契約に必須
フィールドを列挙し `SKILL_DIR/schema.json` の場所を渡す（rejected の形、
`agent_id` を落とす、`claimed_root_cause`）/ F3 対象由来テキスト（ログ本文・
record 本文）をノンス付きタグで囲む / F4 `prior_status` 全 11 値の意味と前回
findings の渡し方 / F5 `--knowledge` は Phase 0 で `classes.py check-knowledge`
を走らせる / F6 「TARGET は書かない」を「親は書かない。許可コマンドの書込は
`writes` に列挙」に直す / F7 `RUN/agents/` の mkdir、`note` は RUN がある時だけ /
F8 quick で abandon 後に残った planned は defer、Phase 5 の `incomplete` 語彙、
同じ候補に 3 人目の verifier は立てない / F9 architecture.md では指示めいた文を
引かず `file:line` のみ / F10 批評に `unresolved` と未割当の面の実体を渡し、
`already_present` は無視してよいと書く / F11 単位数の目安と `selected_classes`
の基準、`excluded_classes` の書式 / F12 dirty な対象では持ち越しの前提が崩れる
注意 / F13 状態の正は RUN のファイル（履歴要約から値を取らない）。

## G. 狩りクラスの内容

| # | 指摘 | 判定 | 直し方 |
|---|------|------|--------|
| G1 | generic#Cryptography and secrets の第 2 文（弱い暗号・タイミング比較・乱数）は出典に無い。未引用の出典 5 件（L1372 / L638 / L655 / stdin unbounded / internal IDs / retry safety） | 採用 | 出典の無い文を削り、Source 行を補う |
| G2 | covered 条件が出典より狭い・弱い・逆: Path confinement（出典は 3 救済、「follows no link」ではない）、Places compared by name（identity **かつ** 畳んだ名前）、Credential follows a redirect（カスタムヘッダは剥がれない）、Lenient parsers（mime では寛容な読みが救済） | 採用 | 出典どおりに書き直す |
| G3 | mcp#Server-authored text treated as fact のサーバ側の救済は出典に無い（RFP の表に由来） | 採用 | 出典にある形（他サーバの description を素通しする proxy / aggregator、結果中の第三者テキストに印が無い）に絞る。RFP の表も直す |
| G4 | mcp#Third-party text reaches a terminal or log raw は cli 側と同文 | 採用 | mcp 側を削除（cli.md 冒頭が「サーバの CLI 面も」と宣言済み） |
| G5 | agent#Right operation, wrong value は covered になり得る単位が無い | 採用 | 出典どおり「設計文書が運用統制（差分レビュー）を名指ししていれば covered、なければ hardening note」 |
| G6 | agent#Forbidden tool refused instead of absent は出典自身が「封じ込めではない」と言う | 採用 | hardening であると本文に書く |
| G7 | generic と製品型のクラスが同じ出典を引き、同じ点検が 2 単位になる | 採用 | SKILL.md Phase 1 に「製品型クラスが精密化する generic クラスは `excluded_classes` に理由 `refined by …` で落とす」 |
| G8 | 読解で判定できない bar（cage の実効、DNS 再束縛、work_dir の実機挙動） | 採用 | 各クラスに「読解で決まらなければ needs_validation」を 1 行 |
| G9 | 同種なのに無い教訓 10 件 | 保留 | 出典補強としての 3 件（stdin unbounded / internal IDs / retry safety）は G1 で採用。新クラスの追加は容量（agent-runtime.md 残 283 B）と「水増ししない」から Phase 2 で判断。特に「緩める設定が呼び出し側のファイルから読める」は横断クラスとして候補 |
| G10 | 残り 7 件の細部（例外の欠落: 機械生成データは plain Unmarshal、マーカーファイルの temp+rename、事前設定ポリシーは自己承認でない、など） | 採用 | 該当クラスに例外を 1 行ずつ |

## H. 文書

| # | 指摘 | 判定 | 直し方 |
|---|------|------|--------|
| H1 | RFP §2 の表に `abandon` / `replacements.json` / `proposals.json` / `agents/` が無い。§4 が `carry` のまま | 採用 | 表を更新 |
| H2 | 残余リスクの未記載: `run.py exec` はファイルシステムを隔離せず対象のテストが run dir・HOME・スキル自身の scripts に書ける。「検証者は hunter のプロンプトを見ていない」はスクリプトで閉じられない。`env_allow` の名前拒否リストは閉じない | 文書 | RFP §3 の残余リスクと README に書く |

## I. テスト

ミューテーション 21 件のうち 18 件が未固定（exec の cwd 脱出、candidates の
リンク、重複 fingerprint、canonical_ref の制御文字、`plain()` の `|`、`writes`
の相対パス、reassign の状態制限、decisions ⊆ result_fingerprints、絶対パス
拒否、minLength の strip、check_log の実在、source_digests 非空、blocked 規則、
台帳ソート、reviewed_paths = checks の和、```` フェンス分断、など）。採用:
A〜E の各修正にテストを付け、未固定 18 件にも pin を足す。

## 不採用

- 新クラス 10 件の一括追加（G9）: 容量と RFP の方針。Phase 2 の候補として記録。
- サブエージェント定義ファイルの同梱（A3 後半）: Skill が agents を同梱できる
  かを確かめてから。今は SKILL.md の起動指定で受ける。
- exec ログの生保存（D4）: 出典どおりファイルへは verbatim。

## 適用順（リスク順）

C1 → B1 / B2 → A1 / A2 / A3 / A7 → D1–D3 → E → F → G → H → I。

---

# 2 回目（2026-11-08、区切り (4) の修正 `26fdbc4..e0a7f61` に対して）

検証者 2 本（スクリプト: 1 回目の再現を再実行して迂回を探す / SKILL.md・
クラス・文書の整合）。1 回目の採用項目はすべて「拒否または正しい動作」を
再現で確認。以下は新たに通ったものだけ。重さは 1 回目より下がった（high は
文章の 1 件のみ）ので、採用分を区切り (5) で直したあと検証の巡は打ち切り、
E2E へ進む（[リスク評価は細部で複雑化しない](../../../CLAUDE.md) の方針）。

## S. スクリプト（修正の隣）

| # | 指摘 | 深刻度 | 判定 | 直し方 |
|---|------|--------|------|--------|
| S1 | `approve` 後に `set-budget` で上限を上げられ、承認が残る | medium | 採用 | 承認後の `set-budget` は拒む（増額は `approve --budget` だけ） |
| S2 | `assign` の spent は親の `count` 自己申告。`count` を呼ばなければ予算を素通り | medium | 採用 | `assign` が hunter の呼び出しを自分で加算する（SKILL.md の `count hunter` は再実行時だけ） |
| S3 | planned が減ると予備枠が縮み、見積より多くのハンターが通る | medium-low | 採用 | `expected_candidates` を planned＋in_progress から出す |
| S4 | `add` は coverage_ids の存在しか見ず、主張した単位と結び付かないレコードが両 validate 緑で報告に載る | medium | 採用 | 初回 add はキューの候補レコードの coverage_ids と一致を要求、`cross_check` は coverage_ids ⊆ fp を持つ単位を検査 |
| S5 | `missing` / `symlink` / `too-large` が source_digests に入り同値比較で「不変」。存在しないファイルを根拠にした confirmed が報告に載る（再現済） | medium | 採用 | record と単位の digest は 64 桁 hex 以外を拒む、`digests_unchanged` は hex 以外を含めば False |
| S6 | `commands.json` の `source` に改行を入れるとログのヘッダを偽装でき、timeout したログが根拠に通る | medium-low | 採用 | コマンド台帳の文字列に改行を禁じ、ヘッダは最初の出現を採る |
| S7 | 判定済み fingerprint を持つ単位の再割当後、判定を変える置換が再判定できず `complete` は通る | medium-low | 採用 | 再判定は archive 済み attempt の decisions も更新、`set-status complete` は validate と cross_check を通す |
| S8 | 批評者・偵察・decide を経ない検証者の id は台帳に入らず、役割をまたぐ再利用を捕まえない | low-medium | 採用 | `used_agent_ids` は candidates / notes / replacements の agent も集め、`merge-critic` は批評者 id を記録 |
| S9 | 直接引用したファイルに大きさの上限が無い（3 GiB sparse を全読） | low | 採用 | 通常ファイルにも bytes 上限 |
| S10 | stderr が違反値を生で反射する（制御文字が親の端末へ） | low | 採用 | `die` / `fail_if` が制御文字を落とす |
| S11 | 同じ `--prior` を二度渡すと carried / suppressed が重複 | low | 採用 | realpath で重複排除 |
| S12 | 同じ fp が carried（後の run の needs_validation）かつ suppressed（前の run の rejected） | low | 採用 | carried になった fp は suppressed から外す |
| S13 | unversioned 分枝の repo 名が形の縛りを通らない | low | 採用 | 同じ整形を通す |
| S14 | `commondir` の判定が任意の祖先を認める | low | 採用 | `gitdir == common/worktrees/<name>` を要求 |
| S15 | 対象内の symlink 経由の出力先は identity では外なので受理され、名前上は対象内 | low | 採用 | 出力先の絶対パスの祖先が名前上対象内なら拒む |
| S16 | `init --output <既存ファイル>` が traceback | low | 採用 | `is_dir` を見て die |
| S17 | `decide --agent` が未狩りの単位を合成 check で candidate にする | low | 保留 | 持ち越しの再検証はその単位の証拠だと解する。AGENTS に注記 |
| S18 | blocked を残したまま `complete` が通る | low | 採用 | complete は blocked も拒む（defer か再割当） |
| S19 | 未固定 8 件（agent id の checks、起動失敗ログ、cross_check の 2 検査、`approve --budget 0`、dict キーの制御文字、pending だけの complete、attempts の同一所有者） | — | 採用 | pin |

## T. SKILL.md・クラス・文書

| # | 指摘 | 深刻度 | 判定 | 直し方 |
|---|------|--------|------|--------|
| T1 | generic.md に origin と一字一句同じ文が 1 つ、近い言い回しが 7 箇所。LICENSE / README の「原文は含まない」と矛盾 | high | 採用 | 同一文を書き換え、近似は語順と構成を変える |
| T2 | mcp#Server-authored text の「MCP 結果を書き換えて無害化しない」は引用見出しに無い | medium | 採用 | その文の出典（security.md「Making text inert at the ingress …」）を Source に加える |
| T3 | `run.py count` が「適用成功の後」にあり、捨てた返りを数えない | medium | 採用 | 起動ごと・適用前に count（Phase 5 と同じ） |
| T4 | 再検証者プロンプトに `<target-data>` と exit_code の明示が無い。批評者に渡す unresolved / uncovered の文も包む対象 | medium | 採用 | Phase 4 と同じ文を Phase 5 と批評者に |
| T5 | 「Refines generic X」が自由散文で、親が機械的に excluded_classes を作れない。generic の origin レンズが除外で消える | medium | 採用 | `Refines:` 行を `Source:` と同格にし、`classes.py list` に出し、`check-knowledge` で存在検査。SKILL.md の除外条件は「generic の残りの教訓がその surface に当たらないとき」 |
| T6 | ハンター契約の列挙に `fingerprint` が無い / `prior_blocked` の意味 / `--prior` の順序 / 変更ソースの前回レコードの行き先 / `budget_reserved` の deferred を残して complete / `checks_unavailable` のトリガー / keep の notes / `carried_from` の保持 / agents/ の「受領のまま」 | low | 採用 | 各 1 句。前回レコードは `changed_prior` として報告へ |
| T7 | cli#Absolute paths の Refines が generic 側の出典と不一致 / Parsers の covered 条件に MIME の救済が無い / G8 の needs_validation と blocked の区別 / Right operation と Forbidden tool の disposition | low | 採用 | 各 1 句 |
| T8 | AGENTS の 8 KB と出典 2 種の残り、RFP の 8 KB・「どちらか」の残り、「14 点」（F は 13 件＋A3・G7） | low | 採用 | 揃える |
| T9 | mcp と agent-runtime の Server-authored text が同じ出典（プロキシ兼ランタイムで二重単位） | low | 保留 | 製品型どうしの重複は規則外。Phase 2 |
