// Landing-Page-Polish: Reveal-on-scroll, Topbar-Schatten beim Scrollen,
// dezenter Typewriter-Effekt fürs Hero-Sub.

const reveal = (el) => el.classList.add("revealed");

if ("IntersectionObserver" in window) {
  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          reveal(entry.target);
          io.unobserve(entry.target);
        }
      }
    },
    { rootMargin: "0px 0px -10% 0px", threshold: 0.05 }
  );

  for (const el of document.querySelectorAll(
    ".section, .step, .feature, .role-card, .pipeline-stage"
  )) {
    el.classList.add("reveal");
    io.observe(el);
  }
} else {
  for (const el of document.querySelectorAll(
    ".section, .step, .feature, .role-card, .pipeline-stage"
  )) {
    el.classList.add("reveal", "revealed");
  }
}

// Topbar bekommt Schatten, sobald gescrollt wird.
const topbar = document.querySelector(".topbar");
if (topbar) {
  const onScroll = () => {
    if (window.scrollY > 8) topbar.classList.add("scrolled");
    else topbar.classList.remove("scrolled");
  };
  document.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}

// Inject reveal-styles inline statt eigenes CSS-File: hält die Slice klein.
const styleEl = document.createElement("style");
styleEl.textContent = `
  .reveal { opacity: 0; transform: translateY(16px); transition: opacity 0.6s ease, transform 0.6s ease; }
  .reveal.revealed { opacity: 1; transform: none; }
  @media (prefers-reduced-motion: reduce) {
    .reveal, .reveal.revealed { opacity: 1; transform: none; transition: none; }
    .character, .hero-logo, .caret, .pipeline-stage.stage-running { animation: none !important; }
  }
  .topbar.scrolled { box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
`;
document.head.appendChild(styleEl);
