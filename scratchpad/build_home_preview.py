# -*- coding: utf-8 -*-
"""홈.py의 현재 디자인을 정적 HTML 스냅샷으로 만든다 (샘플 데이터 기반, 기능 없음)."""
import pathlib

ROOT = pathlib.Path(r"C:\Users\12cog\timetable-recommender")
B64_PATH = pathlib.Path(
    r"C:\Users\12cog\AppData\Local\Temp\claude\C--Users-12cog\61ce4d1b-f1c8-44ad-948f-4e63b287240f\scratchpad\logo_b64.txt"
)
OUT_PATH = ROOT / "scratchpad" / "home_preview.html"

logo_b64 = B64_PATH.read_text(encoding="ascii").strip()

HTML = """<!doctype html>
<title>Upgreender 홈</title>
<meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --teal:#0F766E; --teal-dark:#0B5D57; --teal-tint:#E7F4F2; --teal-pale:#F3FAF9;
  --ink:#101312; --ink-soft:#3F4644; --muted:#6B726F; --faint:#9AA0A0;
  --border:#E7E7E4; --border-soft:#EFEFEC; --surface:#FFFFFF; --canvas:#FAFAF8;
  --amber:#B45309; --amber-tint:#FDF3E7; --red:#B3261E; --red-tint:#FBEAE9;
  --radius-lg:18px; --radius-md:12px; --radius-sm:8px;
  --shadow-sm: 0 1px 2px rgba(16,19,18,.04), 0 1px 1px rgba(16,19,18,.03);
}
* { box-sizing:border-box; }
body{
  margin:0; background:var(--canvas); color:var(--ink-soft);
  font-family:'Pretendard','Manrope',-apple-system,BlinkMacSystemFont,'Malgun Gothic',sans-serif;
  font-variant-numeric:tabular-nums;
}
.shell{ display:flex; min-height:100vh; }

/* ── 사이드바 ── */
.sidebar{
  width:220px; flex:0 0 auto; background:var(--surface); border-right:1px solid var(--border);
  padding:20px 14px; display:flex; flex-direction:column; gap:2px;
}
.side-brand{ display:flex; align-items:center; gap:8px; padding:6px 10px 18px; }
.side-brand img{ height:20px; width:auto; display:block; }
.side-brand span{ font-size:16px; font-weight:800; color:var(--ink); letter-spacing:-.02em; }
.navlink{
  display:flex; align-items:center; gap:10px; padding:9px 10px; border-radius:10px;
  font-size:13.5px; font-weight:600; color:var(--ink-soft); text-decoration:none;
}
.navlink .ic{ width:18px; text-align:center; }
.navlink.active{ background:var(--teal-tint); color:var(--teal-dark); }

/* ── 메인 ── */
main{ flex:1 1 auto; padding:26px 34px 48px; max-width:1180px; }
.topbar{ display:flex; align-items:center; justify-content:space-between; gap:16px; }
.brand-row{ display:flex; align-items:center; gap:10px; }
.brand-row img{ height:24px; width:auto; display:block; }
.brand-row .name{ font-size:19px; font-weight:800; letter-spacing:-.02em; color:var(--ink); }
.term-pill{
  background:var(--teal-tint); color:var(--teal-dark); border-radius:20px; padding:3px 12px;
  font-size:12px; font-weight:600;
}
.upcoming{ font-size:13px; color:var(--muted); }
.user-chip{ text-align:right; }
.user-chip b{ color:var(--ink); font-size:13.5px; }
.user-chip .sub{ color:var(--muted); font-size:12.5px; }

.greeting{ margin:26px 0 4px; }
.greeting h1{ font-size:22px; font-weight:800; color:var(--ink); margin:0 0 4px; letter-spacing:-.01em; text-wrap:balance; }
.greeting p{ margin:0; color:var(--muted); font-size:13.5px; }

.grid{ display:grid; grid-template-columns:1.55fr 1fr; gap:22px; margin-top:26px; align-items:start; }
.col{ display:flex; flex-direction:column; gap:6px; }
.section-title{ font-size:14.5px; font-weight:800; letter-spacing:-.01em; margin:18px 0 10px; color:var(--ink); }
.section-title:first-child{ margin-top:0; }

.card{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
  box-shadow:var(--shadow-sm); padding:18px;
}
.card + .card{ margin-top:10px; }

.next-class{ display:flex; align-items:center; justify-content:space-between; gap:14px; }
.next-class .name{ font-size:16px; font-weight:700; color:var(--ink); margin:0 0 4px; }
.next-class .meta{ color:var(--muted); font-size:13px; }
.countdown{
  background:var(--teal-pale); color:var(--teal-dark); border-radius:14px; padding:6px 14px;
  font-size:13px; font-weight:700; white-space:nowrap;
}

.insight-row{ display:flex; align-items:center; gap:14px; }
.icon-badge{
  flex:0 0 auto; width:40px; height:40px; border-radius:10px; display:flex;
  align-items:center; justify-content:center; font-size:16px; font-weight:800;
}
.icon-badge.red{ background:var(--red-tint); color:var(--red); }
.icon-badge.teal{ background:var(--teal-tint); color:var(--teal-dark); }
.icon-badge.amber{ background:var(--amber-tint); color:var(--amber); }
.insight-title{ font-size:13.5px; font-weight:700; margin:0 0 2px; color:var(--ink); }
.insight-sub{ font-size:12px; color:var(--muted); margin:0; }

.credit-total{ font-size:28px; font-weight:800; color:var(--ink); }
.credit-total .of{ font-size:16px; color:var(--muted); font-weight:500; }
.bar-track{ background:var(--border-soft); border-radius:20px; height:8px; margin:12px 0 6px; overflow:hidden; }
.bar-fill{ background:var(--teal); height:100%; border-radius:20px; }
.pct-label{ font-size:12.5px; color:var(--muted); margin:0 0 4px; }

.stat-line{
  display:flex; align-items:center; justify-content:space-between; padding:9px 0;
  font-size:13px; border-top:1px solid var(--border-soft);
}
.stat-line:first-child{ border-top:none; }
.stat-line .lbl{ color:var(--ink-soft); font-weight:600; }
.stat-line .val{ font-weight:700; }
.val-warn{ color:var(--red); }
.val-good{ color:var(--teal-dark); }

.rec-item{ display:flex; align-items:center; justify-content:space-between; gap:12px; }
.rec-item .name{ font-weight:700; color:var(--ink); font-size:13.5px; margin:0 0 2px; }
.rec-item .reason{ color:var(--muted); font-size:13px; }
.rec-item .link{ color:var(--teal-dark); font-size:13px; font-weight:600; white-space:nowrap; }

.footer-note{ margin-top:28px; font-size:12.5px; color:var(--faint); }

@media (max-width:880px){
  .sidebar{ display:none; }
  .grid{ grid-template-columns:1fr; }
}

@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --surface:#15201E; --canvas:#0E1614; --ink:#F2F5F4; --ink-soft:#CBD3D1; --muted:#8B948F; --faint:#5E6763;
    --border:#243230; --border-soft:#1D2926;
    --teal-tint:#123B37; --teal-pale:#0F2C29; --amber-tint:#3A2A12; --red-tint:#3A1815;
  }
}
:root[data-theme="dark"]{
  --surface:#15201E; --canvas:#0E1614; --ink:#F2F5F4; --ink-soft:#CBD3D1; --muted:#8B948F; --faint:#5E6763;
  --border:#243230; --border-soft:#1D2926;
  --teal-tint:#123B37; --teal-pale:#0F2C29; --amber-tint:#3A2A12; --red-tint:#3A1815;
}
</style>

<div class="shell">
  <nav class="sidebar">
    <div class="side-brand"><img src="data:image/png;base64,__LOGO__" alt=""><span>Upgreender</span></div>
    <a class="navlink active" href="#"><span class="ic">⌂</span>홈</a>
    <a class="navlink" href="#"><span class="ic">▤</span>성적표 업로드</a>
    <a class="navlink" href="#"><span class="ic">🎓</span>수강</a>
    <a class="navlink" href="#"><span class="ic">◎</span>추천 시간표</a>
    <a class="navlink" href="#"><span class="ic">📌</span>내 시간표</a>
    <a class="navlink" href="#"><span class="ic">▦</span>통합 캘린더</a>
    <a class="navlink" href="#"><span class="ic">✦</span>캠퍼스 지도</a>
  </nav>

  <main>
    <div class="topbar">
      <div class="brand-row">
        <img src="data:image/png;base64,__LOGO__" alt="">
        <span class="name">Upgreender</span>
        <span class="term-pill">2026년 2학기</span>
      </div>
      <div class="upcoming">일정 2</div>
      <div class="user-chip"><b>지민</b><div class="sub">컴퓨터공학과 · 3학년</div></div>
    </div>

    <div class="greeting">
      <h1>안녕하세요, 지민님</h1>
      <p>컴퓨터공학과 · 3학년 이수 현황을 한눈에 보여드릴게요</p>
    </div>

    <div class="grid">
      <div class="col">
        <p class="section-title">다음 수업</p>
        <div class="card">
          <div class="next-class">
            <div>
              <p class="name">운영체제</p>
              <p class="meta">화요일 10:00 · 김민준 교수</p>
            </div>
            <div class="countdown">1일 6시간 남음</div>
          </div>
        </div>

        <p class="section-title">지금 확인해보세요</p>
        <div class="card">
          <div class="insight-row">
            <div class="icon-badge red">A</div>
            <div><p class="insight-title">전공필수 3학점이 부족해요</p><p class="insight-sub">이번 학기 과목 선택에서 먼저 확인해보세요.</p></div>
          </div>
        </div>
        <div class="card">
          <div class="insight-row">
            <div class="icon-badge teal">T</div>
            <div><p class="insight-title">팀플 없는 과목 9개를 찾았어요</p><p class="insight-sub">강의계획서 16개를 비교했어요.</p></div>
          </div>
        </div>
        <div class="card">
          <div class="insight-row">
            <div class="icon-badge amber">T</div>
            <div><p class="insight-title">화요일 수업이 3개로 가장 많아요</p><p class="insight-sub">시간표를 다시 확인해보세요.</p></div>
          </div>
        </div>
      </div>

      <div class="col">
        <p class="section-title">이번 학기</p>
        <div class="card">
          <div class="credit-total">19<span class="of"> / 46 학점</span></div>
          <div class="bar-track"><div class="bar-fill" style="width:41%"></div></div>
          <p class="pct-label">졸업까지 41%</p>
        </div>
        <div class="card">
          <div class="stat-line"><span class="lbl">필수교양</span><span class="val val-warn">2학점 부족</span></div>
          <div class="stat-line"><span class="lbl">중핵교양</span><span class="val val-warn">3학점 부족</span></div>
          <div class="stat-line"><span class="lbl">토대교양</span><span class="val val-warn">3학점 부족</span></div>
          <div class="stat-line"><span class="lbl">전공필수</span><span class="val val-warn">3학점 부족</span></div>
          <div class="stat-line"><span class="lbl">전공선택</span><span class="val val-warn">12학점 부족</span></div>
          <div class="stat-line"><span class="lbl">일반선택</span><span class="val val-warn">4학점 부족</span></div>
          <div class="stat-line"><span class="lbl">이번 학기 예정</span><span class="val">15학점</span></div>
        </div>

        <p class="section-title">추천 과목</p>
        <div class="card">
          <div class="rec-item">
            <div><p class="name">운영체제</p><p class="reason">전공필수 · 팀플 없음</p></div>
            <span class="link">추천 시간표에서 보기 ›</span>
          </div>
        </div>
        <div class="card">
          <div class="rec-item">
            <div><p class="name">컴퓨터네트워크</p><p class="reason">전공선택 · 팀플 있음</p></div>
            <span class="link">추천 시간표에서 보기 ›</span>
          </div>
        </div>
        <div class="card">
          <div class="rec-item">
            <div><p class="name">심리통계입문</p><p class="reason">일반선택 · 팀플 없음</p></div>
            <span class="link">추천 시간표에서 보기 ›</span>
          </div>
        </div>
      </div>
    </div>

    <p class="footer-note">
      API 키 상태, 샘플 데이터 불러오기, 사용 안내는 '성적표 업로드' 페이지에서 확인할 수 있습니다.
      선택한 시간표는 '내 시간표' 페이지에서 볼 수 있습니다.
    </p>
  </main>
</div>
"""

OUT_PATH.write_text(HTML.replace("__LOGO__", logo_b64), encoding="utf-8")
print("saved:", OUT_PATH, OUT_PATH.stat().st_size, "bytes")
