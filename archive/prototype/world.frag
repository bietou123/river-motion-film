#version 330 core
in vec2 vUV;
out vec4 fragColor;

uniform float uTime;
uniform float uScene;
uniform vec2 uResolution;
uniform sampler2D uNoise;

float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float noise(vec2 p) {
    return texture(uNoise, p / 512.0).r;
}

float fbm(vec2 p) {
    float n = 0.0, a = 0.5;
    for (int i = 0; i < 4; i++) {
        n += noise(p) * a;
        p = p * 2.07 + 21.3;
        a *= 0.5;
    }
    return n;
}

float segment(vec2 p, vec2 a, vec2 b) {
    vec2 q = p - a, d = b - a;
    return length(q - d * clamp(dot(q, d) / dot(d, d), 0.0, 1.0));
}

float box2(vec2 p, vec2 size) {
    vec2 d = abs(p) - size;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

vec3 over(vec3 background, vec3 foreground, float mask) {
    return mix(background, foreground, clamp(mask, 0.0, 1.0));
}

float paint(float distanceField, float feather) {
    return 1.0 - smoothstep(-feather, feather, distanceField);
}

vec3 atmosphere(vec2 uv, float sunX, vec3 zenith, vec3 horizon, vec3 sunColor, float seconds) {
    float y = 1.0 - uv.y;
    vec3 color = mix(horizon, zenith, smoothstep(0.0, 0.93, y));
    vec2 sun = uv - vec2(sunX, 0.29);
    float glow = exp(-dot(sun, sun) * 35.0);
    color += sunColor * glow * 0.64;
    color += sunColor * exp(-dot(sun, sun) * 650.0) * 0.75;
    float clouds = fbm(uv * vec2(3.0, 7.0) + vec2(seconds * 0.009, 1.4));
    float bank = smoothstep(0.63, 0.85, clouds) * smoothstep(0.61, 0.22, uv.y);
    color = mix(color, color + vec3(0.11, 0.10, 0.08), bank * 0.48);
    return color;
}

vec3 riverScene(vec2 uv, float seconds, float variation) {
    float sunX = 0.63 + 0.07 * sin(seconds * 0.007);
    vec3 color = atmosphere(uv, sunX, vec3(0.024, 0.092, 0.145),
        vec3(0.80, 0.37, 0.23), vec3(1.0, 0.55, 0.22), seconds);
    float m1 = 0.465 + 0.055 * sin(uv.x * 9.1 + variation) +
        0.031 * sin(uv.x * 25.0) + 0.023 * (noise(vec2(uv.x * 55.0, 2.3)) - 0.5);
    float m2 = 0.525 + 0.067 * sin(uv.x * 7.7 + 2.0) +
        0.019 * sin(uv.x * 34.0 + 4.0);
    color = over(color, vec3(0.15, 0.27, 0.31), smoothstep(m1 - 0.003, m1 + 0.003, uv.y));
    color = over(color, vec3(0.087, 0.18, 0.21), smoothstep(m2 - 0.003, m2 + 0.003, uv.y));

    float waterY = 0.56;
    float floorMask = smoothstep(waterY - 0.018, waterY + 0.018, uv.y);
    float depth = 1.8 / max(uv.y - waterY + 0.035, 0.017);
    float forward = depth + seconds * 0.72;
    float transverse = (uv.x - 0.5) * depth * 2.2;
    float meander = 2.1 * sin(forward * 0.065 + variation) +
                    0.34 * sin(forward * 0.19);
    float bank = abs(transverse - meander) - 7.0;
    float bankMask = smoothstep(-0.9, 0.9, bank);
    float flow = sin(transverse * 1.4 + forward * 0.65 + seconds * 1.9) *
                 sin(forward * 1.7 - seconds * 1.2) * 0.5 + 0.5;
    float glitter = pow(max(0.0, sin(forward * 5.0 + seconds * 1.9 + transverse * 1.8)), 12.0);
    float reflectedSun = exp(-abs(uv.x - sunX - 0.035 * sin(forward * 0.2)) * 15.0)
                       * (0.27 + 0.73 * glitter) * (0.2 + 0.8 * (uv.y - waterY));
    vec3 water = mix(vec3(0.025, 0.16, 0.20), vec3(0.06, 0.29, 0.32), flow * 0.6);
    water += vec3(1.0, 0.48, 0.23) * reflectedSun * 0.9;
    vec3 earth = mix(vec3(0.12, 0.20, 0.16), vec3(0.23, 0.30, 0.18),
                     noise(vec2(transverse * 0.42, forward * 0.45)));
    earth *= 0.6 + 0.45 * smoothstep(-0.2, 4.0, bank);
    color = mix(color, mix(water, earth, bankMask), floorMask);

    // A moving human silhouette and boat anchor the changing landscape.
    vec2 boat = uv - vec2(0.32 + sin(seconds * 0.09) * 0.025, 0.655 + sin(seconds * 0.7) * 0.005);
    float hull = paint(box2(boat - vec2(0.0, 0.021), vec2(0.079, 0.010)), 0.002);
    float mast = paint(segment(boat, vec2(-0.008, -0.065), vec2(-0.008, 0.008)) - 0.0018, 0.001);
    float sail = paint(box2(boat - vec2(0.018, -0.030), vec2(0.025, 0.028)), 0.009);
    float person = paint(segment(boat, vec2(-0.04, 0.015), vec2(-0.04, -0.012)) - 0.004, 0.001);
    color = over(color, vec3(0.023, 0.041, 0.049), hull + mast + person);
    color = over(color, vec3(0.86, 0.69, 0.46), sail * 0.83);
    float wake = exp(-abs(boat.y - 0.036) * 360.0) *
                 smoothstep(0.08, 0.01, abs(boat.x + 0.15)) * 0.14;
    color += vec3(0.38, 0.78, 0.70) * wake;
    return color;
}

vec3 warehouseScene(vec2 uv, float seconds, float variation) {
    vec3 color = atmosphere(uv, 0.67, vec3(0.016, 0.055, 0.071),
        vec3(0.17, 0.22, 0.22), vec3(0.6, 0.75, 0.66), seconds);
    vec2 p = uv - 0.5;
    float progress = seconds * 0.7;
    float horizon = 0.43;
    float depth = 0.7 / max(uv.y - horizon, 0.017);
    float x = p.x * depth * 2.2;
    float z = depth + progress;
    float floorMask = smoothstep(horizon, horizon + 0.02, uv.y);
    float floorLight = 0.42 + 0.12 * noise(vec2(x * 0.8, z * 0.3));
    vec3 floorColor = vec3(0.09, 0.14, 0.145) * floorLight * 2.0;
    float gridX = 1.0 - smoothstep(0.0, 0.035, abs(fract(x / 2.4) - 0.5));
    float gridZ = 1.0 - smoothstep(0.0, 0.035, abs(fract(z / 4.0) - 0.5));
    floorColor += vec3(0.25, 0.46, 0.42) * (gridX + gridZ) * 0.26;
    color = mix(color, floorColor, floorMask);

    float vanishing = 0.5 + 0.08 * sin(seconds * 0.15 + variation);
    for (int i = 0; i < 9; i++) {
        float fi = float(i);
        float offset = fract(fi / 9.0 + seconds * 0.14);
        float scale = 0.005 + 0.46 * offset * offset;
        float shelfX = 0.37 + scale;
        float yTop = 0.44 - scale * 1.0;
        float yFoot = 0.44 + scale * 1.65;
        float line1 = 1.0 - smoothstep(0.0015, 0.003, segment(uv, vec2(vanishing - shelfX, yTop), vec2(vanishing - shelfX, yFoot)));
        float line2 = 1.0 - smoothstep(0.0015, 0.003, segment(uv, vec2(vanishing + shelfX, yTop), vec2(vanishing + shelfX, yFoot)));
        float cross = 1.0 - smoothstep(0.001, 0.003, segment(uv, vec2(vanishing - shelfX, yTop), vec2(vanishing + shelfX, yTop)));
        color = over(color, mix(vec3(0.29, 0.35, 0.32), vec3(0.64, 0.51, 0.32), offset),
                     (line1 + line2 + cross) * (0.15 + offset * 0.85));
    }
    vec2 robot = uv - vec2(vanishing + sin(seconds * 0.4) * 0.11, 0.77);
    float body = paint(box2(robot, vec2(0.13, 0.043)), 0.007);
    float top = paint(box2(robot + vec2(0.0, 0.056), vec2(0.09, 0.023)), 0.007);
    float wheel = paint(length(robot - vec2(-0.089, 0.04)) - 0.022, 0.004) +
                  paint(length(robot - vec2(0.089, 0.04)) - 0.022, 0.004);
    color = over(color, vec3(0.03, 0.09, 0.10), body + top + wheel);
    float led = exp(-dot((robot - vec2(0.0, -0.04)) * vec2(6.0, 33.0),
                        (robot - vec2(0.0, -0.04)) * vec2(6.0, 33.0)) * 5.0);
    color += vec3(0.20, 0.98, 0.70) * led * (0.58 + 0.4 * sin(seconds * 2.0));
    return color;
}

vec3 excavatorScene(vec2 uv, float seconds, float variation) {
    vec3 color = atmosphere(uv, 0.69, vec3(0.018, 0.042, 0.057),
        vec3(0.32, 0.22, 0.15), vec3(1.0, 0.49, 0.24), seconds);
    float horizon = 0.61 + 0.04 * sin(uv.x * 16.0 + variation) +
                    0.026 * noise(vec2(uv.x * 52.0, 1.0));
    float ground = smoothstep(horizon - 0.004, horizon + 0.004, uv.y);
    vec3 dirt = vec3(0.16, 0.15, 0.125) * (0.6 + 0.55 * noise(uv * 13.0 + vec2(0.0, seconds * 0.06)));
    color = mix(color, dirt, ground);
    vec2 origin = vec2(0.42 + sin(seconds * 0.019) * 0.08, 0.69);
    vec2 p = uv - origin;
    float excavatorBody = paint(box2(p, vec2(0.105, 0.050)), 0.005);
    float cabin = paint(box2(p + vec2(0.026, 0.060), vec2(0.050, 0.048)), 0.004);
    float track = paint(box2(p - vec2(0.0, 0.064), vec2(0.14, 0.023)), 0.005);
    float a = 0.33 * sin(seconds * 0.35);
    vec2 jointA = origin + vec2(0.064, -0.038);
    vec2 jointB = jointA + vec2(0.145 + a * 0.08, -0.20 + a * 0.07);
    vec2 jointC = jointB + vec2(0.15, 0.085 + 0.055 * sin(seconds * 0.49));
    vec2 bucket = jointC + vec2(0.014, 0.10 + 0.04 * sin(seconds * 0.57));
    float boom = paint(segment(uv, jointA, jointB) - 0.017, 0.003);
    float arm = paint(segment(uv, jointB, jointC) - 0.012, 0.003);
    float wrist = paint(segment(uv, jointC, bucket) - 0.009, 0.002);
    float blade = paint(box2(uv - bucket - vec2(0.016, 0.0), vec2(0.037, 0.019)), 0.006);
    color = over(color, vec3(0.09, 0.11, 0.105), cabin + track);
    color = over(color, vec3(0.71, 0.39, 0.16), excavatorBody + boom + arm + wrist);
    color = over(color, vec3(0.07, 0.10, 0.10), blade);
    for (int j = 0; j < 3; j++) {
        vec2 pivot = j == 0 ? jointA : (j == 1 ? jointB : jointC);
        color = over(color, vec3(0.94, 0.68, 0.33),
            paint(length(uv - pivot) - 0.008, 0.001));
    }
    vec2 flood = uv - vec2(0.76, 0.47);
    color += vec3(0.85, 0.78, 0.54) * exp(-dot(flood, flood) * 66.0) * 0.28;
    for (int j = 0; j < 3; j++) {
        vec2 cell = uv * vec2(17.0, 8.0) + vec2(float(j) * 8.0, -seconds * (0.45 + float(j) * 0.12));
        float streak = 1.0 - smoothstep(0.0, 0.06, abs(fract(cell.x + cell.y * 0.21) - hash21(floor(cell))));
        color += vec3(0.13, 0.21, 0.22) * streak * 0.03;
    }
    return color;
}

vec3 cityScene(vec2 uv, float seconds, float variation) {
    vec3 color = atmosphere(uv, 0.78, vec3(0.016, 0.031, 0.053),
        vec3(0.13, 0.11, 0.16), vec3(0.72, 0.35, 0.28), seconds);
    float horizon = 0.53;
    for (int side = 0; side < 2; side++) {
        float coord = side == 0 ? uv.x : 1.0 - uv.x;
        float column = floor(coord * 14.0);
        float height = 0.19 + 0.31 * hash21(vec2(column, variation + 3.0));
        float building = smoothstep(height, height + 0.005, uv.y) *
                         (1.0 - smoothstep(0.36, 0.40, coord));
        vec3 wall = mix(vec3(0.035, 0.047, 0.057), vec3(0.07, 0.062, 0.083), hash21(vec2(column, 5.0)));
        color = mix(color, wall, building);
        float window = step(0.18, fract(coord * 42.0)) * step(0.16, fract(uv.y * 46.0)) *
                       step(0.48, hash21(vec2(floor(coord * 42.0), floor(uv.y * 46.0))));
        color += vec3(0.91, 0.59, 0.27) * window * building * 0.25;
    }
    float depth = 0.65 / max(uv.y - horizon, 0.012);
    float roadX = (uv.x - 0.5 + 0.04 * sin(seconds * 0.09)) * depth;
    float road = smoothstep(0.46, 0.5, uv.y) * (1.0 - smoothstep(4.5, 4.8, abs(roadX)));
    float z = depth + seconds * 3.0;
    float lane = 1.0 - smoothstep(0.0, 0.08, abs(fract(z / 4.0) - 0.5));
    color = mix(color, vec3(0.055, 0.073, 0.085), road);
    color += vec3(0.93, 0.68, 0.35) * lane *
             exp(-abs(abs(roadX) - 1.7) * 9.0) * road * 0.4;
    float rain = pow(1.0 - smoothstep(0.0, 0.08,
        abs(fract(uv.x * 133.0 + uv.y * 24.0 + seconds * 1.6) - 0.5)), 4.0);
    color += vec3(0.30, 0.43, 0.48) * rain * 0.13;
    return color;
}

void main() {
    vec2 uv = vUV;
    float aspect = uResolution.x / uResolution.y;
    vec2 imageUV = (uv - 0.5) * vec2(aspect / (16.0 / 9.0), 1.0) + 0.5;
    float scene = floor(uScene + 0.1);
    float drift = floor(uTime / 75.0) * 0.31;
    vec3 color;
    if (scene < 0.5 || scene > 10.5) {
        color = riverScene(imageUV, uTime, drift);
    } else if (scene < 2.5 || scene > 8.5 && scene < 9.5) {
        color = warehouseScene(imageUV, uTime, drift);
    } else if (scene < 4.5) {
        color = excavatorScene(imageUV, uTime, drift);
    } else {
        color = cityScene(imageUV, uTime, drift);
    }
    if (scene > 5.5 && scene < 8.5) {
        color = mix(color, riverScene(imageUV, uTime * 0.34, drift + 1.4), 0.24);
    }
    // Luminance, finite film grain and a restrained lens vignette.
    float vignette = 1.0 - 0.66 * pow(length((uv - 0.5) * vec2(1.0, 1.12)), 2.0);
    float grain = hash21(floor(gl_FragCoord.xy * 0.75) + floor(uTime * 60.0)) - 0.5;
    color = max(color * vignette + grain * 0.012, vec3(0.0));
    color = pow(color, vec3(0.92));
    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
