/**
 * A warped lattice of fine white segments. Positions live in typed arrays and
 * are rewritten in place each frame — no allocations on the animation path.
 */
export const LINE_ROWS = 26;
export const LINE_COLS = 40;

const WIDTH = 18;
const DEPTH = 14;

export class LineField {
  readonly positions: Float32Array;
  readonly colors: Float32Array;
  readonly segmentCount: number;
  private readonly gx: Float32Array;
  private readonly gz: Float32Array;
  private readonly shade: Float32Array;

  constructor() {
    const verts = LINE_ROWS * LINE_COLS;
    this.gx = new Float32Array(verts);
    this.gz = new Float32Array(verts);
    this.shade = new Float32Array(verts);

    const rowSegs = LINE_ROWS * (LINE_COLS - 1);
    const colStride = 3;
    const colSegs = Math.ceil(LINE_COLS / colStride) * (LINE_ROWS - 1);
    this.segmentCount = rowSegs + colSegs;
    this.positions = new Float32Array(this.segmentCount * 6);
    this.colors = new Float32Array(this.segmentCount * 6);

    for (let r = 0; r < LINE_ROWS; r++) {
      for (let c = 0; c < LINE_COLS; c++) {
        const i = r * LINE_COLS + c;
        const nx = c / (LINE_COLS - 1);
        const nz = r / (LINE_ROWS - 1);
        this.gx[i] = (nx - 0.5) * WIDTH;
        this.gz[i] = (nz - 0.5) * DEPTH;
        const radial = 1 - Math.min(1, Math.hypot(nx - 0.5, nz - 0.5) * 1.7);
        this.shade[i] = 0.22 + radial * 0.55 + (r % 5 === 0 ? 0.12 : 0);
      }
    }
  }

  /**
   * `scroll` 0–1, `time` seconds, `pointer` in -1..1.
   * Waves lift and the sheet shears as the page moves.
   */
  write(scroll: number, time: number, pointerX: number, pointerY: number): void {
    const t = Math.min(1, Math.max(0, scroll));
    const amp = 0.28 + t * 0.72;
    const freq = 0.42 + t * 0.38;
    const phase = time * (0.22 + t * 0.35);
    const shear = pointerX * 0.55 + t * 1.15;
    const lift = pointerY * 0.25;

    const yOf = (i: number): number => {
      const x = this.gx[i] ?? 0;
      const z = this.gz[i] ?? 0;
      return (
        Math.sin(x * freq + z * 0.38 + phase) * amp +
        Math.sin(z * 0.7 - x * 0.18 - phase * 0.65) * amp * 0.38 +
        x * 0.04 * shear +
        lift
      );
    };

    let s = 0;
    const pos = this.positions;
    const col = this.colors;
    const writeSeg = (a: number, b: number) => {
      const ax = this.gx[a] ?? 0;
      const ay = yOf(a);
      const az = this.gz[a] ?? 0;
      const bx = this.gx[b] ?? 0;
      const by = yOf(b);
      const bz = this.gz[b] ?? 0;
      const o = s * 6;
      pos[o] = ax;
      pos[o + 1] = ay;
      pos[o + 2] = az;
      pos[o + 3] = bx;
      pos[o + 4] = by;
      pos[o + 5] = bz;
      const sa = this.shade[a] ?? 0.3;
      const sb = this.shade[b] ?? 0.3;
      // Warm paper-white with a hint of mint, matching --text / --muted.
      col[o] = 0.9 * sa;
      col[o + 1] = 0.92 * sa;
      col[o + 2] = 0.89 * sa;
      col[o + 3] = 0.9 * sb;
      col[o + 4] = 0.92 * sb;
      col[o + 5] = 0.89 * sb;
      s += 1;
    };

    for (let r = 0; r < LINE_ROWS; r++) {
      for (let c = 0; c < LINE_COLS - 1; c++) {
        const i = r * LINE_COLS + c;
        writeSeg(i, i + 1);
      }
    }
    for (let c = 0; c < LINE_COLS; c += 3) {
      for (let r = 0; r < LINE_ROWS - 1; r++) {
        const i = r * LINE_COLS + c;
        writeSeg(i, i + LINE_COLS);
      }
    }
  }
}
