import { beforeEach, describe, expect, it } from "vitest";

import { Hud } from "../static/hud.js";

function setupHudDom() {
  document.body.innerHTML = `
    <div id="hud-release" class="hud-pill"><span class="hud-value">0%</span></div>
    <div id="hud-pipeline" class="hud-pill"><span class="hud-value">100%</span></div>
    <div id="hud-coffee" class="hud-pill"><span class="hud-value">100%</span></div>
    <div id="hud-incidents" class="hud-pill"><span class="hud-value">0%</span></div>
    <div id="hud-timer" class="hud-pill"><span class="hud-value">--:--</span></div>
    <div id="hud-role" class="hud-pill">Rolle: —</div>
  `;
}

describe("Hud", () => {
  beforeEach(setupHudDom);

  it("setStats updates the percentage values", () => {
    const hud = new Hud();
    hud.setStats({
      releaseProgress: 42,
      pipelineStability: 88,
      coffeeLevel: 12,
      incidents: 7,
    });
    expect(document.querySelector("#hud-release .hud-value").textContent).toContain("42");
    expect(document.querySelector("#hud-pipeline .hud-value").textContent).toContain("88");
    expect(document.querySelector("#hud-coffee .hud-value").textContent).toContain("12");
    expect(document.querySelector("#hud-incidents .hud-value").textContent).toContain("7");
  });

  it("setTimer formats remaining seconds as mm:ss", () => {
    const hud = new Hud();
    hud.setTimer(125); // 2:05
    expect(document.querySelector("#hud-timer .hud-value").textContent).toMatch(/2:05|02:05/);
  });

  it("setRole writes the role label", () => {
    const hud = new Hud();
    hud.setRole("vibe_coder", "chaos_agents");
    const text = document.getElementById("hud-role").textContent;
    expect(text.length).toBeGreaterThan(5);
  });
});
