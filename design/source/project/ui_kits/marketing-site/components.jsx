// DKube marketing-site UI kit components
const { useState } = React;

const ArrowTopRight = ({size=14}) => (
  <svg className="arr" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M7 17 17 7M9 7h8v8"/>
  </svg>
);

const ArrowRight = ({size=14}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M5 12h14M13 6l6 6-6 6"/>
  </svg>
);

const Plus = ({size=14}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M12 5v14M5 12h14"/>
  </svg>
);

const Button = ({ children, variant='primary', icon=true, onClick }) => (
  <button className={`dk-btn dk-btn-${variant}`} onClick={onClick}>
    {children}
    {icon && (variant === 'ghost' ? <ArrowRight/> : <ArrowTopRight/>)}
  </button>
);

const Header = ({ active, onNav }) => {
  const items = ['Home','Blueprints','Platforms','Case Studies','Team','Resources'];
  return (
    <header className="dk-header">
      <div className="dk-container dk-header-inner">
        <a href="#home" className="dk-logo" onClick={(e)=>{e.preventDefault();onNav('Home');}}>
          <img src="../../assets/dkube-logo-purple.svg" alt="DKube"/>
        </a>
        <nav className="dk-nav">
          {items.map(i => (
            <a key={i} href={`#${i}`} onClick={(e)=>{e.preventDefault();onNav(i);}}
               style={active===i?{color:'var(--dk-brand)'}:{}}>{i}</a>
          ))}
        </nav>
        <Button variant="primary">Contact Us</Button>
      </div>
    </header>
  );
};

const Hero = () => (
  <section className="dk-hero">
    <div className="dk-container">
      <div className="dk-hero-eyebrow">Private AI for Enterprise</div>
      <h1>Private AI</h1>
      <div className="dk-hero-marquee">
        <span className="brand">Govern Your AI Expense and Data Residency</span>
        <span>Audit & Compliance Ready</span>
        <span>Production-Ready Application in Weeks</span>
      </div>
      <p className="dk-hero-lede">
        DKube helps enterprises design, deploy, and scale secure, private AI systems —
        across on-prem, private cloud, and hybrid environments — without compromising
        control, compliance, or ownership.
      </p>
      <div style={{display:'flex',gap:14}}>
        <Button variant="primary">Talk to Us</Button>
        <Button variant="secondary">Our 12-Weeks Commitment</Button>
      </div>
    </div>
  </section>
);

const TrustStrip = () => (
  <section className="dk-container" style={{paddingTop:24, paddingBottom:64}}>
    <p className="dk-trust-caption">Trusted by enterprises and innovation-driven organizations worldwide</p>
    <div className="dk-logo-strip">
      <img src="../../assets/logo-vmware.svg" alt="VMware"/>
      <img src="../../assets/logo-cisco.svg" alt="Cisco"/>
      <img src="../../assets/logo-vmware.svg" alt="VMware" style={{opacity:0}}/>
      <img src="../../assets/logo-cisco.svg" alt="Cisco" style={{opacity:0}}/>
      <span style={{fontFamily:'var(--dk-font-display)',fontSize:18,fontWeight:700,color:'var(--dk-fg-2)'}}>FUNGIBLE</span>
      <span style={{fontFamily:'var(--dk-font-display)',fontSize:18,fontWeight:700,color:'var(--dk-fg-2)'}}>ALTOS LABS</span>
      <span style={{fontFamily:'var(--dk-font-display)',fontSize:18,fontWeight:700,color:'var(--dk-fg-2)'}}>STACKPATH</span>
      <span style={{fontFamily:'var(--dk-font-display)',fontSize:18,fontWeight:700,color:'var(--dk-fg-2)'}}>APOLLO</span>
      <span style={{fontFamily:'var(--dk-font-display)',fontSize:18,fontWeight:700,color:'var(--dk-fg-2)'}}>TIAA</span>
    </div>
  </section>
);

const Pillars = () => (
  <section className="dk-section">
    <div className="dk-container">
      <h2 className="dk-section-head">From experimentation to enterprise-grade, production-ready AI in weeks.</h2>
      <div className="dk-pillars">
        {[
          {icon:'icon-magic.svg', title:'Private AI', desc:'Deploy securely within your infrastructure — on-prem, private cloud, or hybrid.'},
          {icon:'icon-trust.svg', title:'Enterprise Trust', desc:'Audit-ready governance, compliance controls, and full data residency.'},
          {icon:'icon-scalable.svg', title:'Scalable Delivery', desc:'A 12-week structured engagement model from discovery to production.'},
        ].map(p => (
          <div className="dk-pillar" key={p.title}>
            <div className="dk-pillar-icon"><img src={`../../assets/${p.icon}`}/></div>
            <h3>{p.title}</h3>
            <p>{p.desc}</p>
          </div>
        ))}
      </div>
      <div className="dk-stats">
        {[
          {n:'12', l:'Weeks Enterprise-Ready Solution Delivery'},
          {n:'15', l:'Years of Enterprise Expertise'},
          {n:'120', l:'Team Strength of AI Experts'},
        ].map(s => (
          <div className="dk-stat" key={s.l}>
            <div className="dk-stat-num">+{s.n}</div>
            <div className="dk-stat-label">{s.l}</div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

const Blueprints = () => {
  const cards = [
    { img:'img-querilynx.avif', tags:['Finance','Construction'], title:'QueriLynx',
      desc:'A unified, multi-agent platform that lets users explore data from various sources using no code.'},
    { img:'img-vta.jpg', tags:['Education'], title:'Virtual Teaching Assistant',
      desc:'A RAG-native AI copilot that streamlines teaching tasks, personalizes learning, and enhances student engagement.'},
    { img:'img-docmind.avif', tags:['Finance','Insurance'], title:'DocMind',
      desc:'An AI-driven document assistant that streamlines workflows through intelligent sorting and key field extraction.'},
  ];
  return (
    <section className="dk-section dk-section-tint">
      <div className="dk-container">
        <h2 className="dk-section-head">Enterprise AI Blueprints designed for real-world impact.</h2>
        <div className="dk-cards-3">
          {cards.map(c => (
            <article className="dk-blueprint" key={c.title}>
              <div className="dk-blueprint-img"><img src={`../../assets/${c.img}`}/></div>
              <div className="dk-blueprint-body">
                <div className="dk-blueprint-tags">
                  {c.tags.map(t => <span className="dk-blueprint-tag" key={t}>{t}</span>)}
                </div>
                <h3>{c.title}</h3>
                <span className="dk-blueprint-explore">Explore <ArrowRight/></span>
                <p className="dk-blueprint-desc">{c.desc}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

const Platforms = () => {
  const [tab, setTab] = useState('DKubeX');
  const data = {
    DKubeX: { eyebrow:'GenAI ModelOps', title:'DKubeX',
      blurb:'An enterprise-grade private AI platform to build, deploy, and scale Generative AI and ML securely within your infrastructure.'},
    DKube:  { eyebrow:'MLOps', title:'DKube',
      blurb:'An end-to-end MLOps platform that enables AI/ML & data engineering teams to build, train, and deploy complex ML models.'},
  };
  const d = data[tab];
  return (
    <section className="dk-section">
      <div className="dk-container">
        <h2 className="dk-section-head">Platforms that power our solutions.</h2>
        <div className="dk-tabs">
          {Object.keys(data).map(k => (
            <div key={k} className={`dk-tab ${tab===k?'active':''}`} onClick={()=>setTab(k)}>{k}</div>
          ))}
        </div>
        <div style={{
          background:'var(--dk-white)', border:'1px solid var(--dk-border)',
          borderRadius:'var(--dk-radius-xl)', padding:'48px',
          display:'grid', gridTemplateColumns:'1.2fr 1fr', gap:48, alignItems:'center',
          boxShadow:'var(--dk-shadow-sm)'
        }}>
          <div>
            <div className="dk-eyebrow-mark" style={{marginBottom:12}}>{d.eyebrow}</div>
            <h3 style={{fontFamily:'var(--dk-font-display)',fontSize:48,fontWeight:800,letterSpacing:'-0.02em',margin:'0 0 16px',color:'var(--dk-fg)'}}>{d.title}</h3>
            <p style={{fontSize:17,lineHeight:1.6,color:'var(--dk-fg-1)',margin:'0 0 24px',maxWidth:520}}>{d.blurb}</p>
            <Button variant="primary">Learn More</Button>
          </div>
          <div style={{
            aspectRatio:'4/3',
            background:'linear-gradient(135deg,#9384BD 0%,#7660A8 60%,#4A3878 100%)',
            borderRadius:'var(--dk-radius-lg)',
            position:'relative', overflow:'hidden'
          }}>
            <div style={{position:'absolute',inset:24,border:'1px solid rgba(255,255,255,0.25)',borderRadius:'var(--dk-radius-md)',padding:20,color:'#fff'}}>
              <div style={{fontSize:11,letterSpacing:'0.06em',textTransform:'uppercase',opacity:0.7,fontWeight:600,marginBottom:8}}>{d.eyebrow}</div>
              <div style={{fontFamily:'var(--dk-font-display)',fontSize:32,fontWeight:800}}>{d.title}</div>
              <div style={{position:'absolute',bottom:20,left:20,right:20,display:'flex',gap:6,flexWrap:'wrap'}}>
                {(tab==='DKubeX'?['RAG','Agents','Vector DB','Guardrails']:['Pipelines','Notebooks','Serving','Monitoring']).map(t=>(
                  <span key={t} style={{fontSize:11,fontWeight:600,padding:'4px 10px',background:'rgba(255,255,255,0.15)',border:'1px solid rgba(255,255,255,0.25)',borderRadius:999}}>{t}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const CaseStudies = () => {
  const cases = [
    { img:'img-bi.avif', title:'Business Intelligence', tags:['Data Insights','Text-to-SQL']},
    { img:'img-mortgage.jpg', title:'Mortgage Document Processing', tags:['Private AI','RAG']},
    { img:'img-construction.avif', title:'Construction Digital Twin', tags:['QueriLynx','AI Copilot']},
    { img:'img-vta.jpg', title:'Higher Education Copilot', tags:['Education','RAG']},
  ];
  return (
    <section className="dk-section dk-section-tint">
      <div className="dk-container">
        <h2 className="dk-section-head">How enterprises operationalize AI. Confidently.</h2>
        <div className="dk-cases">
          {cases.map(c => (
            <article className="dk-case" key={c.title}>
              <img src={`../../assets/${c.img}`}/>
              <div className="dk-case-scrim"/>
              <div className="dk-case-meta">
                <h4>{c.title}</h4>
                <div className="dk-case-tags">
                  {c.tags.map(t => <span className="dk-case-tag" key={t}>{t}</span>)}
                </div>
              </div>
              <div className="dk-case-arrow"><ArrowTopRight size={18}/></div>
            </article>
          ))}
        </div>
        <div style={{marginTop:40,textAlign:'center'}}>
          <Button variant="secondary">Explore All Case Studies</Button>
        </div>
      </div>
    </section>
  );
};

const FAQ = () => {
  const [open, setOpen] = useState(0);
  const items = [
    { q:'What does DKube deliver?', a:'DKube designs and delivers secure Private AI solutions—covering discovery, development, deployment, and ongoing maintenance.'},
    { q:'How fast can we go from idea to production?', a:'Most engagements follow our structured 12-week delivery model, tailored to your use case and deployment needs.'},
    { q:'What is the engagement model?', a:'Engagement is scoped around outcomes and delivery phases. We align on requirements, milestones, and operational expectations early.'},
    { q:'Do you support post-deployment operations?', a:'Yes. DKube provides continuous maintenance and support from development through deployment—and beyond.'},
    { q:'How do we collaborate during delivery?', a:'You get frequent checkpoints across discovery, MVP delivery, pilot feedback, refinement, and deployment—so progress stays visible.'},
    { q:'How do we get started with DKube?', a:'Start with a short discovery call. We\u2019ll align on the use case, constraints, and delivery plan to move quickly into execution.'},
  ];
  return (
    <section className="dk-section">
      <div className="dk-container">
        <h2 className="dk-section-head">Got questions? We've got answers.</h2>
        <div className="dk-faq">
          {items.map((it, i) => (
            <div key={i} className={`dk-faq-item ${open===i?'open':''}`} onClick={()=>setOpen(open===i?-1:i)}>
              <div className="dk-faq-q">
                <span>{it.q}</span>
                <span className="dk-faq-toggle"><Plus/></span>
              </div>
              <div className="dk-faq-a"><div className="dk-faq-a-inner">{it.a}</div></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

const FinalCTA = () => (
  <section style={{padding:'48px 0 96px'}}>
    <div className="dk-container">
      <div className="dk-cta">
        <h2>Build AI you can deploy, operate, and trust.</h2>
        <Button variant="primary">Talk to Us</Button>
      </div>
    </div>
  </section>
);

const Footer = () => (
  <footer className="dk-footer">
    <div className="dk-container">
      <div className="dk-footer-grid">
        <div className="dk-footer-brand">
          <img src="../../assets/dkube-logo-purple.svg" alt="DKube"/>
          <p>Designing and delivering secure Private AI solutions for enterprises.</p>
        </div>
        <div className="dk-footer-col">
          <h5>Company</h5>
          <a href="#">Home</a><a href="#">About Us</a><a href="#">Contact Us</a>
        </div>
        <div className="dk-footer-col">
          <h5>Products</h5>
          <a href="#">DKube</a><a href="#">DKubeX</a>
        </div>
        <div className="dk-footer-col">
          <h5>Blueprints</h5>
          <a href="#">QueriLynx</a><a href="#">VTA</a><a href="#">DocMind</a>
        </div>
        <div className="dk-footer-col">
          <h5>Knowledge</h5>
          <a href="#">Case Studies</a><a href="#">Resources</a><a href="#">Docs</a>
        </div>
      </div>
      <div className="dk-footer-bottom">
        <span>©2026 One Convergence. All Rights Reserved.</span>
        <div className="dk-footer-socials">
          <a href="#"><img src="../../assets/si-linkedin.svg"/></a>
          <a href="#"><img src="../../assets/si-twitter.svg"/></a>
          <a href="#"><img src="../../assets/si-insta.svg"/></a>
        </div>
      </div>
    </div>
  </footer>
);

Object.assign(window, { Header, Hero, TrustStrip, Pillars, Blueprints, Platforms, CaseStudies, FAQ, FinalCTA, Footer, Button });
