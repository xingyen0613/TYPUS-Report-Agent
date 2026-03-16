TYPUS AI Gen Design Compact

[Chart Design Compact]
- Canvas size: 1400×640（可改，建議固定寬高比 2.1875:1）
- Margins (% of height/width，避免重疊)
  * Top 15%，Bottom 18%，Left 9%，Right 4%
  * 文字區塊：Title band、Subtitle band、Plot area、Key stats band、Source band 依序堆疊
- Palette（可直接換 HEX）
  * Background: #FFFFFF
  * Text & axes: #1D252D
  * Line: #5056EA
  * Grid: #E2E8F0 (dash 5/8)
- Typography（可替換，若系統無則 fallback Helvetica Neue → Arial）
  * Title: Geometos Rounded, 34px, bold, centered
  * Subtitle: PF Spekk VAR Semibold, 20px, centered
  * Axis numbers: PF Spekk VAR Black, 16px
  * Key stats: PF Spekk VAR Semibold, 18px
  * Source: PF Spekk VAR Regular, 14px
- Text placement安全距離
  * Title y=Top margin−10px，Subtitle y=Title+44px
  * Plot area僅占 canvas 中間 60% 高度，確保折線與文字不重疊
  * Key stats 置於 bottom margin−48px
  * Source 置於 bottom margin−15px
- Watermark（可隨時改檔案、尺寸、透明度）
  * File: `/Users/yen/claude/typus-report/design_style/Typus logo_horizontal_navy_square.svg`
  * Placement: canvas 中央，寬 600px（自適應等比高度 263px）
  * Opacity: 0.08（可調 0.05–0.12 視需要）
  * 若換尺寸，建議限制在 plot area 內 60%×60%，避免覆蓋文字區塊
- Auto-overlap check
  * 建圖前依照 canvas × margins 判斷文字 band 是否跨入 plot area；若 subtitle 長度過長，可自動換行或縮字級 2px
  * 若 key stats 內容增減，先量測字串像素寬度，必要時改成多行或縮減 canvas 底部 margin