package com.fpsrealista.client;

/** Oscilador amortiguado para retroceso y balanceo procedurales. */
public final class Spring {
    public float x;
    public float v;
    private final float stiffness;
    private final float damping;

    public Spring(float stiffness, float dampingRatio) {
        this.stiffness = stiffness;
        this.damping = 2f * (float) Math.sqrt(stiffness) * dampingRatio;
    }

    public void update(float dt, float target) {
        float step = 1f / 240f;
        while (dt > 0) {
            float h = Math.min(step, dt);
            float a = -stiffness * (x - target) - damping * v;
            v += a * h;
            x += v * h;
            dt -= h;
        }
    }

    public void impulse(float dv) {
        v += dv;
    }

    public void reset() {
        x = 0;
        v = 0;
    }
}
