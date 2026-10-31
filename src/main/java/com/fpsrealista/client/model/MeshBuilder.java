package com.fpsrealista.client.model;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import java.util.ArrayList;
import java.util.List;

/**
 * Generador de mallas a partir de las primitivas del formato de modelo.
 * Implementacion espejo de tools/gunlib.py (part_quads): cualquier cambio aqui debe
 * reflejarse alli para que las vistas previas coincidan con el juego.
 *
 * Cada vertice: x, y, z (cm), u, v (cm o uv de decal), nx, ny, nz.
 */
public final class MeshBuilder {
    public static final int STRIDE = 8;
    public static final float SMOOTH_DEG = 40f;

    /** Lista de quads; cada quad son 4 vertices de STRIDE floats. */
    public static final class Quads {
        public final List<float[]> quads = new ArrayList<>();

        void add(float[][] v) {
            float[] q = new float[4 * STRIDE];
            for (int i = 0; i < 4; i++) {
                System.arraycopy(v[i], 0, q, i * STRIDE, STRIDE);
            }
            quads.add(q);
        }
    }

    private MeshBuilder() {}

    // ------------------------------------------------------------------ ayudas
    static float[] to3(char axis, float u, float v, float a) {
        return switch (axis) {
            case 'z' -> new float[] {u, v, a};
            case 'x' -> new float[] {a, v, u};
            default -> new float[] {u, a, v};
        };
    }

    static float[] vert(float[] p, float u, float v, float[] n) {
        return new float[] {p[0], p[1], p[2], u, v, n[0], n[1], n[2]};
    }

    static double signedArea(float[][] p) {
        double s = 0;
        for (int i = 0; i < p.length; i++) {
            float[] a = p[i];
            float[] b = p[(i + 1) % p.length];
            s += a[0] * b[1] - b[0] * a[1];
        }
        return s * 0.5;
    }

    private static double cross(float[] o, float[] a, float[] b) {
        return (a[0] - o[0]) * (double) (b[1] - o[1]) - (a[1] - o[1]) * (double) (b[0] - o[0]);
    }

    private static boolean inside(float[] p, float[] a, float[] b, float[] c) {
        return cross(a, b, p) >= -1e-9 && cross(b, c, p) >= -1e-9 && cross(c, a, p) >= -1e-9;
    }

    /** Ear clipping (poligono antihorario). */
    static List<int[]> triangulate(float[][] poly) {
        List<Integer> idx = new ArrayList<>();
        for (int i = 0; i < poly.length; i++) {
            idx.add(i);
        }
        List<int[]> tris = new ArrayList<>();
        int guard = 0;
        while (idx.size() > 3 && guard < 10000) {
            guard++;
            int m = idx.size();
            boolean found = false;
            for (int k = 0; k < m; k++) {
                int i0 = idx.get(Math.floorMod(k - 1, m));
                int i1 = idx.get(k);
                int i2 = idx.get((k + 1) % m);
                float[] a = poly[i0], b = poly[i1], c = poly[i2];
                if (cross(a, b, c) <= 1e-9) {
                    continue;
                }
                boolean ok = true;
                for (int j : idx) {
                    if (j == i0 || j == i1 || j == i2) {
                        continue;
                    }
                    if (inside(poly[j], a, b, c)) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    tris.add(new int[] {i0, i1, i2});
                    idx.remove(k);
                    found = true;
                    break;
                }
            }
            if (!found) {
                for (int k = 1; k < idx.size() - 1; k++) {
                    tris.add(new int[] {idx.get(0), idx.get(k), idx.get(k + 1)});
                }
                return tris;
            }
        }
        if (idx.size() == 3) {
            tris.add(new int[] {idx.get(0), idx.get(1), idx.get(2)});
        }
        return tris;
    }

    static float[][] circle(float cu, float cv, float r, int seg, float phase) {
        float[][] p = new float[seg][];
        for (int k = 0; k < seg; k++) {
            double a = 2 * Math.PI * k / seg + phase;
            p[k] = new float[] {(float) (cu + r * Math.cos(a)), (float) (cv + r * Math.sin(a))};
        }
        return p;
    }

    static float[][] rectProfile(float u0, float v0, float u1, float v1, float b) {
        if (b <= 0) {
            return new float[][] {{u0, v0}, {u1, v0}, {u1, v1}, {u0, v1}};
        }
        b = Math.min(b, Math.min((u1 - u0) / 2 * 0.99f, (v1 - v0) / 2 * 0.99f));
        return new float[][] {{u0 + b, v0}, {u1 - b, v0}, {u1, v0 + b}, {u1, v1 - b},
                {u1 - b, v1}, {u0 + b, v1}, {u0, v1 - b}, {u0, v0 + b}};
    }

    // ------------------------------------------------------------------ loft
    static void loft(Quads out, char axis, float[][] p0, float[][] p1, float a0, float a1, boolean caps,
                     float smoothDeg, boolean flip) {
        int n = p0.length;
        float[][] en = new float[n][];
        for (int i = 0; i < n; i++) {
            float du = p0[(i + 1) % n][0] - p0[i][0];
            float dv = p0[(i + 1) % n][1] - p0[i][1];
            float l = (float) Math.hypot(du, dv);
            if (l == 0) {
                l = 1;
            }
            en[i] = new float[] {dv / l, -du / l};
        }
        double cosT = Math.cos(Math.toRadians(smoothDeg));
        float[] per = new float[n + 1];
        for (int i = 0; i < n; i++) {
            per[i + 1] = per[i] + (float) Math.hypot(p0[(i + 1) % n][0] - p0[i][0], p0[(i + 1) % n][1] - p0[i][1]);
        }
        float sgn = flip ? -1f : 1f;
        for (int e = 0; e < n; e++) {
            int i = e, j = (e + 1) % n;
            float[] ni = vnormal(en, i, e, n, cosT);
            float[] nj = vnormal(en, j, e, n, cosT);
            float[][] v = new float[4][];
            v[0] = vert(to3(axis, p0[i][0], p0[i][1], a0), per[e], a0, to3(axis, ni[0] * sgn, ni[1] * sgn, 0));
            v[1] = vert(to3(axis, p0[j][0], p0[j][1], a0), per[e + 1], a0, to3(axis, nj[0] * sgn, nj[1] * sgn, 0));
            v[2] = vert(to3(axis, p1[j][0], p1[j][1], a1), per[e + 1], a1, to3(axis, nj[0] * sgn, nj[1] * sgn, 0));
            v[3] = vert(to3(axis, p1[i][0], p1[i][1], a1), per[e], a1, to3(axis, ni[0] * sgn, ni[1] * sgn, 0));
            out.add(v);
        }
        if (caps) {
            List<int[]> tris = triangulate(p0);
            float d = a1 >= a0 ? 1f : -1f;
            for (int c = 0; c < 2; c++) {
                float[][] pp = c == 0 ? p0 : p1;
                float a = c == 0 ? a0 : a1;
                float s = c == 0 ? -d : d;
                float[] nrm = to3(axis, 0, 0, s * sgn);
                for (int[] t : tris) {
                    float[][] v = new float[4][];
                    for (int k = 0; k < 3; k++) {
                        float[] q = pp[t[k]];
                        v[k] = vert(to3(axis, q[0], q[1], a), q[0], q[1], nrm);
                    }
                    v[3] = v[2];
                    out.add(v);
                }
            }
        }
    }

    private static float[] vnormal(float[][] en, int i, int e, int n, double cosT) {
        float[] a = en[Math.floorMod(i - 1, n)];
        float[] b = en[i % n];
        if (a[0] * b[0] + a[1] * b[1] >= cosT) {
            float su = a[0] + b[0], sv = a[1] + b[1];
            float l = (float) Math.hypot(su, sv);
            if (l == 0) {
                l = 1;
            }
            return new float[] {su / l, sv / l};
        }
        return en[e];
    }

    // ------------------------------------------------------------------ primitivas
    private static float f(JsonObject o, String k, float def) {
        return o.has(k) ? o.get(k).getAsFloat() : def;
    }

    private static float[] vec(JsonElement e) {
        JsonArray a = e.getAsJsonArray();
        float[] r = new float[a.size()];
        for (int i = 0; i < r.length; i++) {
            r[i] = a.get(i).getAsFloat();
        }
        return r;
    }

    private static float[][] profile(JsonElement e) {
        JsonArray a = e.getAsJsonArray();
        float[][] r = new float[a.size()][];
        for (int i = 0; i < r.length; i++) {
            r[i] = vec(a.get(i));
        }
        return r;
    }

    private static float[][] reversed(float[][] p) {
        float[][] r = new float[p.length][];
        for (int i = 0; i < p.length; i++) {
            r[i] = p[p.length - 1 - i];
        }
        return r;
    }

    public static Quads build(JsonObject part) {
        String type = part.get("type").getAsString();
        float sm = f(part, "smooth", SMOOTH_DEG);
        Quads q = new Quads();
        switch (type) {
            case "box" -> {
                float[] fr = vec(part.get("from"));
                float[] to = vec(part.get("to"));
                float[] lo = new float[3], hi = new float[3], dims = new float[3];
                for (int i = 0; i < 3; i++) {
                    lo[i] = Math.min(fr[i], to[i]);
                    hi[i] = Math.max(fr[i], to[i]);
                    dims[i] = hi[i] - lo[i];
                }
                char axis;
                if (part.has("axis")) {
                    axis = part.get("axis").getAsString().charAt(0);
                } else {
                    int best = 0;
                    for (int i = 1; i < 3; i++) {
                        if (dims[i] > dims[best]) {
                            best = i;
                        }
                    }
                    axis = "xyz".charAt(best);
                }
                float b = f(part, "bevel", 0f);
                float[][] prof;
                float a0, a1;
                if (axis == 'z') {
                    prof = rectProfile(lo[0], lo[1], hi[0], hi[1], b);
                    a0 = lo[2];
                    a1 = hi[2];
                } else if (axis == 'x') {
                    prof = rectProfile(lo[2], lo[1], hi[2], hi[1], b);
                    a0 = lo[0];
                    a1 = hi[0];
                } else {
                    prof = rectProfile(lo[0], lo[2], hi[0], hi[2], b);
                    a0 = lo[1];
                    a1 = hi[1];
                }
                loft(q, axis, prof, prof, a0, a1, true, sm);
            }
            case "cyl" -> {
                char axis = part.has("axis") ? part.get("axis").getAsString().charAt(0) : 'z';
                float[] c = part.has("c") ? vec(part.get("c")) : new float[] {0, 0};
                float r0 = part.get("r").getAsFloat();
                float r1 = f(part, "r2", r0);
                int seg = part.has("seg") ? part.get("seg").getAsInt() : 16;
                float ph = (float) Math.toRadians(f(part, "phase", 0f));
                float[] a = vec(part.get("a"));
                float smc = f(part, "smooth", 60f);
                float[][] po = circle(c[0], c[1], r0, seg, ph);
                float[][] p1 = circle(c[0], c[1], r1, seg, ph);
                if (!part.has("inner")) {
                    loft(q, axis, po, p1, a[0], a[1], true, smc);
                } else {
                    float in0 = part.get("inner").getAsFloat();
                    float in1 = f(part, "inner2", in0);
                    loft(q, axis, po, p1, a[0], a[1], false, smc);
                    float[][] pi0 = circle(c[0], c[1], in0, seg, ph);
                    float[][] pi1 = circle(c[0], c[1], in1, seg, ph);
                    loft(q, axis, pi0, pi1, a[0], a[1], false, smc, true);
                    float d = a[1] >= a[0] ? 1f : -1f;
                    for (int cc = 0; cc < 2; cc++) {
                        float[][] oo = cc == 0 ? po : p1;
                        float[][] ii = cc == 0 ? pi0 : pi1;
                        float aa = a[cc];
                        float[] nrm = to3(axis, 0, 0, cc == 0 ? -d : d);
                        for (int k = 0; k < seg; k++) {
                            int k2 = (k + 1) % seg;
                            q.add(new float[][] {
                                    vert(to3(axis, oo[k][0], oo[k][1], aa), oo[k][0], oo[k][1], nrm),
                                    vert(to3(axis, oo[k2][0], oo[k2][1], aa), oo[k2][0], oo[k2][1], nrm),
                                    vert(to3(axis, ii[k2][0], ii[k2][1], aa), ii[k2][0], ii[k2][1], nrm),
                                    vert(to3(axis, ii[k][0], ii[k][1], aa), ii[k][0], ii[k][1], nrm)});
                        }
                    }
                }
            }
            case "extrude", "loft" -> {
                char axis = part.has("axis") ? part.get("axis").getAsString().charAt(0) : 'x';
                float[][] p0 = profile(part.get("profile"));
                float[][] p1 = part.has("profile2") ? profile(part.get("profile2")) : p0;
                if (signedArea(p0) < 0) {
                    p0 = reversed(p0);
                    p1 = reversed(p1);
                }
                float[] a = vec(part.get("a"));
                boolean caps = !part.has("caps") || part.get("caps").getAsBoolean();
                loft(q, axis, p0, p1, a[0], a[1], caps, sm);
            }
            case "decal" -> {
                float[][] c = profile(part.get("corners"));
                float[] uv = part.has("uv") ? vec(part.get("uv")) : new float[] {0, 0, 1, 1};
                float[] e1 = {c[1][0] - c[0][0], c[1][1] - c[0][1], c[1][2] - c[0][2]};
                float[] e2 = {c[3][0] - c[0][0], c[3][1] - c[0][1], c[3][2] - c[0][2]};
                float[] n = normalize(new float[] {e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2],
                        e1[0] * e2[1] - e1[1] * e2[0]});
                float[][] uvs = {{uv[0], uv[3]}, {uv[2], uv[3]}, {uv[2], uv[1]}, {uv[0], uv[1]}};
                float[][] v = new float[4][];
                for (int i = 0; i < 4; i++) {
                    v[i] = vert(c[i], uvs[i][0], uvs[i][1], n);
                }
                q.add(v);
            }
            default -> throw new IllegalArgumentException("Primitiva desconocida: " + type);
        }

        if (part.has("rot")) {
            float[] rot = vec(part.get("rot"));
            float[] pv;
            if (part.has("pivot")) {
                pv = vec(part.get("pivot"));
            } else {
                float[] mn = {Float.MAX_VALUE, Float.MAX_VALUE, Float.MAX_VALUE};
                float[] mx = {-Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE};
                for (float[] qq : q.quads) {
                    for (int k = 0; k < 4; k++) {
                        for (int d = 0; d < 3; d++) {
                            mn[d] = Math.min(mn[d], qq[k * STRIDE + d]);
                            mx[d] = Math.max(mx[d], qq[k * STRIDE + d]);
                        }
                    }
                }
                pv = new float[] {(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2};
            }
            double[][] R = rotMatrix(rot[0], rot[1], rot[2]);
            for (float[] qq : q.quads) {
                for (int k = 0; k < 4; k++) {
                    int o = k * STRIDE;
                    float px = qq[o] - pv[0], py = qq[o + 1] - pv[1], pz = qq[o + 2] - pv[2];
                    qq[o] = (float) (R[0][0] * px + R[0][1] * py + R[0][2] * pz) + pv[0];
                    qq[o + 1] = (float) (R[1][0] * px + R[1][1] * py + R[1][2] * pz) + pv[1];
                    qq[o + 2] = (float) (R[2][0] * px + R[2][1] * py + R[2][2] * pz) + pv[2];
                    float nx = qq[o + 5], ny = qq[o + 6], nz = qq[o + 7];
                    qq[o + 5] = (float) (R[0][0] * nx + R[0][1] * ny + R[0][2] * nz);
                    qq[o + 6] = (float) (R[1][0] * nx + R[1][1] * ny + R[1][2] * nz);
                    qq[o + 7] = (float) (R[2][0] * nx + R[2][1] * ny + R[2][2] * nz);
                }
            }
        }
        return q;
    }

    static void loft(Quads out, char axis, float[][] p0, float[][] p1, float a0, float a1, boolean caps, float smoothDeg) {
        loft(out, axis, p0, p1, a0, a1, caps, smoothDeg, false);
    }

    static float[] normalize(float[] v) {
        float l = (float) Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
        if (l < 1e-12f) {
            return new float[] {0, 1, 0};
        }
        return new float[] {v[0] / l, v[1] / l, v[2] / l};
    }

    /** R = Rz * Ry * Rx (grados). */
    public static double[][] rotMatrix(double rx, double ry, double rz) {
        rx = Math.toRadians(rx);
        ry = Math.toRadians(ry);
        rz = Math.toRadians(rz);
        double cx = Math.cos(rx), sx = Math.sin(rx), cy = Math.cos(ry), sy = Math.sin(ry), cz = Math.cos(rz), sz = Math.sin(rz);
        double[][] Rx = {{1, 0, 0}, {0, cx, -sx}, {0, sx, cx}};
        double[][] Ry = {{cy, 0, sy}, {0, 1, 0}, {-sy, 0, cy}};
        double[][] Rz = {{cz, -sz, 0}, {sz, cz, 0}, {0, 0, 1}};
        return mul(Rz, mul(Ry, Rx));
    }

    private static double[][] mul(double[][] a, double[][] b) {
        double[][] r = new double[3][3];
        for (int i = 0; i < 3; i++) {
            for (int j = 0; j < 3; j++) {
                r[i][j] = a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j];
            }
        }
        return r;
    }
}
