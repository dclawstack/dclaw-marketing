// kinetic-reel.jsx — 8 kinetic-typography scenes for the DKube reel.
// Designed against a 1080×1920 (9:16) Stage; total duration 19s.
//
// Scene timing (mirrors the brief):
//   00:00–00:02  Scene 1  BREAK OUT  → logo shatter-in
//   00:02–00:06  Scene 2  dkube.io // 01 AMBIENT  (ticker + pulse)
//   00:06–00:08  Scene 3  VOICE CONTROLS ANYTHING (per-letter audio-wave scale)
//   00:08–00:11  Scene 4  02 CONTINUITY  (split-text across two devices)
//   00:11–00:13  Scene 5  SWITCH SEAMLESSLY (blur slide-up)
//   00:13–00:16  Scene 6  03 PARITY  (scale-to-bounding-box)
//   00:16–00:17  Scene 7  ZERO LOCK-IN  (padlock morph)
//   00:17–00:19  Scene 8  DKUBE.IO // EVOLVE NOW  (explosive scale-out)

const REEL = {
  bg: '#0B0F19',
  ink: '#F4F4F8',
  accent: '#B89BF2',  // bright lilac neon — DKube purple boosted for dark mode
  accentDim: '#7660A8',
  font: 'Poppins, system-ui, sans-serif',
  W: 1080,
  H: 1920,
};

// ───────── helpers ─────────
const lerp = (a, b, t) => a + (b - a) * t;

// Format big helpers reused across scenes
const headline = (size, weight = 900) => ({
  fontFamily: REEL.font,
  fontWeight: weight,
  fontSize: size,
  letterSpacing: '-0.04em',
  lineHeight: 0.92,
  textTransform: 'uppercase',
});

// ─────────────────────────────────────────────
// Scene 1 — BREAK OUT → DKube logo
// 0–2s. Heavy type slams down centred (0–0.6s), holds (0.6–1.1s),
// shatters into pieces (1.1–1.6s), reveals DKube cube logo (1.5–2.0s).
function Scene1Break() {
  return (
    <Sprite start={0} end={2.0}>
      {({ localTime }) => {
        // Slam: from off-top + huge to centre
        const slamT = clamp(localTime / 0.55, 0, 1);
        const slam = Easing.easeOutBack(slamT);
        const slamY = lerp(-380, 0, slam);
        const slamScale = lerp(1.6, 1.0, slam);

        // Shatter starts at 1.1s
        const shatterT = clamp((localTime - 1.1) / 0.5, 0, 1);
        const shatter = Easing.easeInQuad(shatterT);
        const shatterOpacity = 1 - shatter;
        const shatterBlur = shatter * 6;

        // Logo reveals at 1.4s
        const logoT = clamp((localTime - 1.4) / 0.5, 0, 1);
        const logo = Easing.easeOutBack(logoT);
        const logoScale = lerp(0.4, 1, logo);

        // Pre-shatter: split text into two halves and tilt during shatter
        const halfTop = -shatter * 80;
        const halfBot = shatter * 80;
        const tilt = shatter * 8;

        return (
          <React.Fragment>
            {shatterOpacity > 0.01 && (
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                opacity: shatterOpacity,
                filter: `blur(${shatterBlur}px)`,
                transform: `translateY(${slamY}px) scale(${slamScale})`,
              }}>
                <div style={{ position: 'relative', textAlign: 'center', color: REEL.ink, ...headline(200, 900), letterSpacing: '-0.05em' }}>
                  {/* top half clipped */}
                  <div style={{
                    position: 'absolute', inset: 0,
                    clipPath: 'polygon(0 0, 100% 0, 100% 50%, 0 50%)',
                    transform: `translate(${-tilt}px, ${halfTop}px) rotate(${-tilt * 0.3}deg)`,
                  }}>BREAK<br/>OUT</div>
                  {/* bottom half clipped */}
                  <div style={{
                    position: 'absolute', inset: 0,
                    clipPath: 'polygon(0 50%, 100% 50%, 100% 100%, 0 100%)',
                    transform: `translate(${tilt}px, ${halfBot}px) rotate(${tilt * 0.3}deg)`,
                  }}>BREAK<br/>OUT</div>
                  {/* placeholder so block sizes correctly */}
                  <span style={{ visibility: 'hidden' }}>BREAK<br/>OUT</span>
                </div>
              </div>
            )}

            {/* Logo reveal */}
            {logoT > 0 && (
              <div style={{
                position: 'absolute',
                left: '50%', top: '50%',
                transform: `translate(-50%, -50%) scale(${logoScale})`,
                opacity: logoT,
                filter: `drop-shadow(0 0 60px ${REEL.accent}80)`,
              }}>
                <img src="../assets/dkube-icon-purple.svg" alt="" style={{ width: 360, height: 360, filter: 'brightness(0) invert(1)' }} />
              </div>
            )}
          </React.Fragment>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene 2 — dkube.io // 01 AMBIENT  (2–6s)
// Ticker tape slides left across the screen carrying "dkube.io //".
// At 3.4s the word AMBIENT lands centred and pulses like a soundwave.
function Scene2Ambient() {
  return (
    <Sprite start={2.0} end={6.0}>
      {({ localTime }) => {
        // Ticker phase 0–1.5s
        const tickerT = clamp(localTime / 1.5, 0, 1);
        const tickerX = lerp(REEL.W + 200, -REEL.W - 800, Easing.easeInOutQuad(tickerT));

        // 01 label & AMBIENT pulse phase from 1.4s onward
        const labelT = clamp((localTime - 1.4) / 0.5, 0, 1);
        const ambientT = clamp((localTime - 1.7) / 0.4, 0, 1);
        const ambientPulse = 1 + Math.sin((localTime - 1.7) * 5.5) * 0.04 * (localTime > 1.7 ? 1 : 0);

        // Soundwave bars under AMBIENT
        const bars = [0.5, 0.85, 0.6, 1.0, 0.7, 0.45, 0.95, 0.55, 0.8, 0.65];

        // Exit fade from 3.6s
        const exitT = clamp((localTime - 3.6) / 0.4, 0, 1);
        const groupOpacity = 1 - exitT;

        return (
          <div style={{ position: 'absolute', inset: 0, opacity: groupOpacity }}>
            {/* Ticker line */}
            <div style={{
              position: 'absolute',
              top: 460,
              left: 0,
              transform: `translateX(${tickerX}px)`,
              whiteSpace: 'nowrap',
              color: REEL.ink,
              ...headline(180, 800),
            }}>
              <span style={{ color: REEL.accent }}>dkube.io</span>
              <span style={{ color: 'rgba(244,244,248,0.35)', margin: '0 60px' }}>//</span>
              <span style={{ color: REEL.ink }}>dkube.io</span>
              <span style={{ color: 'rgba(244,244,248,0.35)', margin: '0 60px' }}>//</span>
              <span style={{ color: REEL.accent }}>dkube.io</span>
            </div>

            {/* "01" big label */}
            <div style={{
              position: 'absolute',
              top: 740,
              left: 80,
              opacity: labelT,
              transform: `translateX(${(1 - labelT) * -40}px)`,
              ...headline(380, 900),
              color: 'transparent',
              WebkitTextStroke: `4px ${REEL.accent}`,
              letterSpacing: '-0.06em',
            }}>01</div>

            {/* AMBIENT pulse */}
            <div style={{
              position: 'absolute',
              top: 1080,
              left: 0,
              width: '100%',
              textAlign: 'center',
              opacity: ambientT,
              transform: `scale(${ambientPulse})`,
              transformOrigin: 'center',
              color: REEL.ink,
              ...headline(220, 900),
              textShadow: `0 0 60px ${REEL.accent}80`,
            }}>AMBIENT</div>

            {/* Soundwave bars */}
            <div style={{
              position: 'absolute',
              top: 1380,
              left: 0,
              width: '100%',
              display: 'flex',
              justifyContent: 'center',
              gap: 18,
              opacity: ambientT,
            }}>
              {bars.map((amp, i) => {
                const wave = (Math.sin((localTime - 1.7) * 6 + i * 0.6) * 0.5 + 0.5) * amp;
                const h = 30 + wave * 200;
                return (
                  <div key={i} style={{
                    width: 22,
                    height: h,
                    background: i % 2 === 0 ? REEL.accent : REEL.ink,
                    borderRadius: 4,
                  }} />
                );
              })}
            </div>

            {/* Voiceover caption */}
            <div style={{
              position: 'absolute',
              bottom: 220,
              left: 0,
              width: '100%',
              textAlign: 'center',
              color: 'rgba(244,244,248,0.55)',
              fontFamily: REEL.font,
              fontWeight: 500,
              fontSize: 36,
              letterSpacing: '-0.005em',
              opacity: ambientT,
            }}>
              Voice assistance, anywhere
            </div>
          </div>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene 3 — VOICE CONTROLS ANYTHING  (6–8s)
// Per-letter scale animation simulating an audio-frequency meter.
function Scene3Voice() {
  const lines = ['VOICE', 'CONTROLS', 'ANYTHING'];
  return (
    <Sprite start={6.0} end={8.0}>
      {({ localTime }) => {
        // Words enter staggered
        return (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            gap: 30,
          }}>
            {lines.map((line, li) => {
              const lineStart = li * 0.18;
              return (
                <div key={li} style={{
                  display: 'flex',
                  gap: 6,
                }}>
                  {line.split('').map((ch, ci) => {
                    const t = clamp((localTime - lineStart - ci * 0.04) / 0.35, 0, 1);
                    const enterScale = Easing.easeOutBack(t);
                    // Audio-wave per-letter pulse
                    const pulseT = localTime - lineStart - ci * 0.06;
                    const pulse = Math.sin(pulseT * 7) * 0.18 + 1;
                    const scaleY = enterScale < 1 ? enterScale : pulse;
                    const opacity = clamp(t, 0, 1);
                    const isAccent = li === 1; // CONTROLS → accent
                    const lineSize = li === 0 ? 200 : li === 1 ? 170 : 180;
                    return (
                      <span key={ci} style={{
                        display: 'inline-block',
                        transform: `scaleY(${scaleY}) scaleX(${enterScale < 1 ? enterScale : 1})`,
                        transformOrigin: 'center bottom',
                        opacity,
                        color: isAccent ? REEL.accent : REEL.ink,
                        ...headline(lineSize, 900),
                      }}>{ch}</span>
                    );
                  })}
                </div>
              );
            })}

            {/* Frequency bar at bottom */}
            <div style={{
              position: 'absolute',
              bottom: 280,
              left: 80, right: 80,
              height: 8,
              background: 'rgba(244,244,248,0.1)',
              borderRadius: 4,
              overflow: 'hidden',
            }}>
              <div style={{
                position: 'absolute',
                left: 0, top: 0, bottom: 0,
                width: `${clamp(localTime / 2, 0, 1) * 100}%`,
                background: REEL.accent,
              }} />
            </div>
          </div>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene 4 — 02 CONTINUITY (8–11s)
// Two device frames pass each other; word splits across them.
function Scene4Continuity() {
  return (
    <Sprite start={8.0} end={11.0}>
      {({ localTime }) => {
        // Devices slide in (0–0.5s), pass mid (1.0–1.8s), exit (2.5–3s)
        const inT = clamp(localTime / 0.5, 0, 1);
        const inE = Easing.easeOutCubic(inT);
        const passT = clamp((localTime - 1.0) / 1.0, 0, 1);
        const passE = Easing.easeInOutQuad(passT);
        const exitT = clamp((localTime - 2.5) / 0.5, 0, 1);
        const exitE = Easing.easeInQuad(exitT);

        // Device 1 slides: enters from left, exits left
        const d1x = lerp(-700, -200, inE) + (1 - exitE) * 0 - exitE * 700;
        // Device 2 slides: enters from right, exits right
        const d2x = lerp(700, 200, inE) + exitE * 700;

        // Crossing position offset
        const cross1 = -passE * 220;
        const cross2 = passE * 220;

        const labelT = clamp((localTime - 0.4) / 0.4, 0, 1);
        const labelE = Easing.easeOutCubic(labelT);

        return (
          <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
            {/* "02" big label top */}
            <div style={{
              position: 'absolute',
              top: 200, left: 0, width: '100%',
              textAlign: 'center',
              opacity: labelE * (1 - exitE),
              ...headline(220, 900),
              color: REEL.accent,
              letterSpacing: '-0.06em',
            }}>02</div>

            {/* Device 1 (laptop) */}
            <div style={{
              position: 'absolute',
              top: 720,
              left: '50%',
              transform: `translateX(calc(-50% + ${d1x + cross1}px))`,
              opacity: clamp(inT - exitT, 0, 1),
            }}>
              <div style={{
                width: 540, height: 360,
                background: '#15192A',
                border: `3px solid ${REEL.accent}`,
                borderRadius: 12,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                paddingRight: 36,
                color: REEL.ink,
                ...headline(140, 900),
                boxShadow: `0 0 60px ${REEL.accent}40`,
                overflow: 'hidden',
              }}>CONTI</div>
              <div style={{
                width: 600, height: 24,
                background: '#1F2438',
                marginTop: -2,
                marginLeft: -30,
                borderBottomLeftRadius: 24,
                borderBottomRightRadius: 24,
              }} />
            </div>

            {/* Device 2 (phone) */}
            <div style={{
              position: 'absolute',
              top: 760,
              left: '50%',
              transform: `translateX(calc(-50% + ${d2x + cross2}px))`,
              opacity: clamp(inT - exitT, 0, 1),
            }}>
              <div style={{
                width: 320, height: 480,
                background: '#15192A',
                border: `3px solid ${REEL.accent}`,
                borderRadius: 36,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-start',
                paddingLeft: 22,
                color: REEL.ink,
                ...headline(110, 900),
                boxShadow: `0 0 60px ${REEL.accent}40`,
                overflow: 'hidden',
              }}>NUITY</div>
            </div>

            {/* Caption */}
            <div style={{
              position: 'absolute',
              bottom: 260, left: 0, width: '100%',
              textAlign: 'center',
              color: 'rgba(244,244,248,0.6)',
              fontFamily: REEL.font, fontWeight: 600, fontSize: 38,
              letterSpacing: '-0.005em',
              opacity: clamp(inT - exitT, 0, 1),
            }}>
              Continuous workflows, every device
            </div>
          </div>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene 5 — SWITCH SEAMLESSLY (11–13s)
// Blurred slide-up between two states.
function Scene5Switch() {
  return (
    <Sprite start={11.0} end={13.0}>
      {({ localTime }) => {
        // Word slides up with motion blur
        const t = clamp(localTime / 0.6, 0, 1);
        const e = Easing.easeOutCubic(t);
        const y = lerp(160, 0, e);
        const blur = (1 - e) * 14;

        const exitT = clamp((localTime - 1.5) / 0.5, 0, 1);
        const exitE = Easing.easeInCubic(exitT);
        const exitY = -exitE * 160;
        const exitBlur = exitE * 14;

        const totalY = y + exitY;
        const totalBlur = blur + exitBlur;
        const opacity = clamp(t, 0, 1) * (1 - exitE);

        return (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            gap: 0,
          }}>
            <div style={{
              transform: `translateY(${totalY}px)`,
              filter: `blur(${totalBlur}px)`,
              opacity,
              color: REEL.ink,
              textAlign: 'center',
              ...headline(220, 900),
            }}>
              SWITCH<br/>
              <span style={{ color: REEL.accent, fontSize: 150 }}>SEAMLESSLY</span>
            </div>

            {/* Animated horizontal motion-line */}
            <div style={{
              position: 'absolute',
              top: 'calc(50% + 220px)',
              left: 0, width: '100%',
              height: 6,
              opacity,
            }}>
              <div style={{
                position: 'absolute',
                left: `${lerp(-30, 100, t)}%`,
                width: 220, height: 6,
                background: REEL.accent,
                filter: `blur(${totalBlur}px)`,
              }} />
            </div>
          </div>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene 6 — 03 PARITY (13–16s)
// Giant letters scale tightly into a bounding box block.
function Scene6Parity() {
  return (
    <Sprite start={13.0} end={16.0}>
      {({ localTime }) => {
        // Letters fly in oversized then crunch into the bounding box (0–1.0s).
        const crunchT = clamp(localTime / 1.0, 0, 1);
        const crunch = Easing.easeInOutBack(crunchT);
        const lettersScale = lerp(2.0, 1.0, crunch);

        // Bounding box draws in 0.4–1.0s
        const boxT = clamp((localTime - 0.4) / 0.6, 0, 1);
        const boxE = Easing.easeOutQuad(boxT);

        // "03" enters
        const labelT = clamp(localTime / 0.5, 0, 1);

        // Caption
        const captionT = clamp((localTime - 1.2) / 0.5, 0, 1);

        // Exit
        const exitT = clamp((localTime - 2.5) / 0.5, 0, 1);
        const opacity = 1 - exitT;

        return (
          <div style={{ position: 'absolute', inset: 0, opacity }}>
            <div style={{
              position: 'absolute',
              top: 240,
              left: 80,
              opacity: labelT,
              transform: `translateX(${(1 - labelT) * -40}px)`,
              ...headline(280, 900),
              color: REEL.accent,
              letterSpacing: '-0.06em',
            }}>03</div>

            {/* Bounding box */}
            <div style={{
              position: 'absolute',
              top: 760,
              left: 80,
              right: 80,
              height: 360,
              border: `5px solid ${REEL.accent}`,
              borderRadius: 14,
              transform: `scaleX(${boxE}) scaleY(${0.3 + 0.7 * boxE})`,
              transformOrigin: 'left center',
              boxShadow: `0 0 50px ${REEL.accent}40`,
            }}>
              <div style={{
                position: 'absolute',
                inset: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: REEL.ink,
                ...headline(220, 900),
                transform: `scale(${lettersScale})`,
                transformOrigin: 'center',
              }}>PARITY</div>
            </div>

            {/* Caption */}
            <div style={{
              position: 'absolute',
              bottom: 360,
              left: 80, right: 80,
              textAlign: 'center',
              opacity: captionT,
              transform: `translateY(${(1 - captionT) * 30}px)`,
              color: 'rgba(244,244,248,0.7)',
              fontFamily: REEL.font, fontWeight: 600, fontSize: 42,
              letterSpacing: '-0.01em',
              lineHeight: 1.2,
            }}>
              Open. Portable.<br/>
              <span style={{ color: REEL.accent }}>Yours.</span>
            </div>
          </div>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene 7 — ZERO LOCK-IN (16–17s)
// Padlock icon morphs to text.
function Scene7Lock() {
  return (
    <Sprite start={16.0} end={17.0}>
      {({ localTime }) => {
        const t = clamp(localTime / 0.5, 0, 1);
        const lockOpacity = 1 - Easing.easeInQuad(t);
        const lockScale = lerp(1, 0.6, Easing.easeInQuad(t));
        const textOpacity = clamp((localTime - 0.3) / 0.4, 0, 1);
        const textScale = lerp(0.8, 1, Easing.easeOutBack(textOpacity));

        return (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {/* Padlock SVG */}
            <svg width="320" height="380" viewBox="0 0 320 380" style={{
              position: 'absolute',
              opacity: lockOpacity,
              transform: `scale(${lockScale})`,
              filter: `drop-shadow(0 0 40px ${REEL.accent}80)`,
            }}>
              <path d="M90 160 V120 a70 70 0 0 1 140 0 V160" stroke={REEL.accent} strokeWidth="20" fill="none" strokeLinecap="round"/>
              <rect x="60" y="160" width="200" height="180" rx="20" fill={REEL.accent}/>
              <circle cx="160" cy="240" r="22" fill={REEL.bg}/>
              <rect x="150" y="240" width="20" height="50" rx="10" fill={REEL.bg}/>
            </svg>

            {/* Cracking line that opens it */}
            <svg width="400" height="400" viewBox="0 0 400 400" style={{
              position: 'absolute',
              opacity: clamp((localTime - 0.15) / 0.2, 0, 1) * (1 - clamp((localTime - 0.4) / 0.2, 0, 1)),
            }}>
              <path d="M50 200 L150 180 L120 220 L220 200 L180 240 L350 220" stroke="#fff" strokeWidth="6" fill="none" strokeLinecap="round"/>
            </svg>

            {/* Text */}
            <div style={{
              opacity: textOpacity,
              transform: `scale(${textScale})`,
              color: REEL.ink,
              textAlign: 'center',
              ...headline(220, 900),
            }}>
              ZERO<br/>
              <span style={{ color: REEL.accent }}>LOCK-IN.</span>
            </div>
          </div>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene 8 — DKUBE.IO // EVOLVE NOW (17–19s)
// Explosive scale outward with bright URL.
function Scene8Outro() {
  return (
    <Sprite start={17.0} end={19.0}>
      {({ localTime }) => {
        // Phase 1: implode 0–0.4s
        const implodeT = clamp(localTime / 0.4, 0, 1);
        const implode = Easing.easeInQuart(implodeT);
        const implodeScale = lerp(2.4, 0.5, implode);
        const implodeOpacity = clamp(localTime / 0.1, 0, 1) * (1 - implode);

        // Phase 2: explode 0.35–0.9s — the URL bursts outward then settles
        const explodeT = clamp((localTime - 0.35) / 0.55, 0, 1);
        const explode = Easing.easeOutBack(explodeT);
        const explodeScale = lerp(0.2, 1, explode);

        // Phase 3: hold + radial flash 0.9–1.4s
        const flashT = clamp((localTime - 0.85) / 0.5, 0, 1);
        const flashOpacity = (1 - flashT) * 0.5;
        const flashScale = lerp(0.5, 2.5, flashT);

        // Phase 4: subtitle EVOLVE NOW slides up 1.2–2s
        const subT = clamp((localTime - 1.2) / 0.5, 0, 1);
        const subY = lerp(60, 0, Easing.easeOutCubic(subT));

        return (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: REEL.bg,
          }}>
            {/* Radial flash */}
            <div style={{
              position: 'absolute',
              left: '50%', top: '50%',
              width: 1400, height: 1400,
              transform: `translate(-50%, -50%) scale(${flashScale})`,
              borderRadius: '50%',
              background: `radial-gradient(circle, ${REEL.accent}AA 0%, transparent 60%)`,
              opacity: flashOpacity,
              pointerEvents: 'none',
            }} />

            {/* Implode pre-text */}
            {implodeOpacity > 0.01 && (
              <div style={{
                position: 'absolute',
                opacity: implodeOpacity,
                transform: `scale(${implodeScale})`,
                color: REEL.ink,
                ...headline(180, 900),
                filter: `blur(${(1 - implode) * 12}px)`,
              }}>BUILD SMART</div>
            )}

            {/* The URL bursts in */}
            <div style={{
              position: 'absolute',
              transform: `scale(${explodeScale})`,
              opacity: explodeT > 0 ? 1 : 0,
              textAlign: 'center',
            }}>
              <div style={{
                color: REEL.accent,
                ...headline(200, 900),
                textShadow: `0 0 60px ${REEL.accent}, 0 0 120px ${REEL.accent}80`,
                letterSpacing: '-0.05em',
              }}>DKUBE.IO</div>
            </div>

            {/* EVOLVE NOW */}
            <div style={{
              position: 'absolute',
              bottom: 380,
              left: 0, width: '100%',
              textAlign: 'center',
              transform: `translateY(${subY}px)`,
              opacity: subT,
            }}>
              <div style={{
                color: REEL.ink,
                fontFamily: REEL.font,
                fontWeight: 600,
                fontSize: 56,
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
              }}>// EVOLVE NOW</div>
            </div>
          </div>
        );
      }}
    </Sprite>
  );
}

// ─────────────────────────────────────────────
// Scene-end progress dots (always visible after Scene 1)
function ProgressDots() {
  const time = useTime();
  const total = 19;
  const sceneStarts = [0, 2, 6, 8, 11, 13, 16, 17];
  const current = sceneStarts.findLastIndex(s => time >= s);
  if (time < 1.6) return null;
  return (
    <div style={{
      position: 'absolute',
      top: 80, left: 80, right: 80,
      display: 'flex', gap: 10, justifyContent: 'flex-start',
      opacity: clamp((time - 1.6) / 0.4, 0, 1),
    }}>
      {sceneStarts.map((_, i) => (
        <div key={i} style={{
          flex: 1,
          height: 6,
          background: i < current ? REEL.accent : i === current ? 'rgba(244,244,248,0.6)' : 'rgba(244,244,248,0.18)',
          borderRadius: 3,
          transition: 'background 200ms',
        }} />
      ))}
    </div>
  );
}

// Watermark (bottom corner) shown after first scene
function Watermark() {
  const time = useTime();
  if (time < 2 || time > 17) return null;
  return (
    <div style={{
      position: 'absolute',
      bottom: 80, left: 80,
      display: 'flex', alignItems: 'center', gap: 16,
      opacity: 0.6,
    }}>
      <img src="../assets/dkube-icon-purple.svg" alt="" style={{ width: 40, height: 40, filter: 'brightness(0) invert(1)' }} />
      <span style={{
        color: REEL.ink,
        fontFamily: REEL.font,
        fontWeight: 600,
        fontSize: 22,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
      }}>dkube.io</span>
    </div>
  );
}

// ─────────────────────────────────────────────
// Reel root
function Reel() {
  return (
    <Stage
      width={REEL.W}
      height={REEL.H}
      duration={19}
      background={REEL.bg}
      loop={true}
      autoplay={true}
      persistKey="dkube-reel"
    >
      <Scene1Break />
      <Scene2Ambient />
      <Scene3Voice />
      <Scene4Continuity />
      <Scene5Switch />
      <Scene6Parity />
      <Scene7Lock />
      <Scene8Outro />
      <ProgressDots />
      <Watermark />
    </Stage>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<Reel />);
