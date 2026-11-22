import { describe, expect, it } from "vitest";
import {
  convertArea,
  convertMass,
  EVIDENCE_LABELS,
  fmtCoord,
  fmtNum,
  fmtUsd,
} from "../utils/format";

describe("Salvadoran agricultural unit conversions and scientific formatting", () => {
  it("converts manzanas and hectares accurately (1 mz = 0.70 ha)", () => {
    expect(convertArea(1, "mz", "ha")).toBeCloseTo(0.7, 5);
    expect(convertArea(0.7, "ha", "mz")).toBeCloseTo(1.0, 5);
    expect(convertArea(5, "mz", "mz")).toBe(5);
  });

  it("converts quintales (46 kg), kilograms, and metric tons", () => {
    expect(convertMass(1, "qq", "kg")).toBe(46);
    expect(convertMass(1000, "kg", "t")).toBe(1);
    expect(convertMass(1, "t", "qq")).toBeCloseTo(1000 / 46, 4);
  });

  it("renders explicit unavailable text instead of fabricating zeroes", () => {
    expect(fmtNum(null)).toBe("No disponible");
    expect(fmtNum(undefined)).toBe("No disponible");
    expect(fmtNum(Number.NaN)).toBe("No disponible");
    expect(fmtUsd(null)).toBe("No disponible");
    expect(fmtCoord(13.6894, -89.1872)).toContain("13.6894° N");
  });

  it("maps every scientific evidence class to an accessible label and tone", () => {
    expect(EVIDENCE_LABELS.reanalysis.label).toContain("Reanálisis");
    expect(EVIDENCE_LABELS.synthetic_scenario.tone).toBe("synthetic");
    expect(EVIDENCE_LABELS.field_observation.tone).toBe("warn");
    expect(EVIDENCE_LABELS.unavailable.tone).toBe("unavailable");
  });
});
