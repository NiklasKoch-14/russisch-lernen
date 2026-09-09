import { describe, expect, it } from "vitest";

import { rectStyle } from "./rect";

describe("rectStyle", () => {
  it("rundet die Fliesskomma-Reste weg", () => {
    // 0.14 * 100 ist 14.000000000000002 — ungerundet stuende das im style.
    expect(rectStyle({ x: 0.03, y: 0.36, w: 0.14, h: 0.42 })).toEqual({
      left: "3%",
      top: "36%",
      width: "14%",
      height: "42%",
    });
  });

  it("behaelt echte Nachkommastellen", () => {
    expect(rectStyle({ x: 0.125, y: 0, w: 0.5, h: 1 }).left).toBe("12.5%");
  });
});
