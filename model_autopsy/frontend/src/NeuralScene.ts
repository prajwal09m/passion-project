/* NeuroScene — the Model Autopsy hero centerpiece.
 *
 * An animated "model under forensic examination": a particle nebula
 * shot through with fine connecting filaments, three pulsing anomaly
 * cores, and drifting data streams. Pointer causes parallax rotation;
 * page scroll changes composition/energy. Rendered with Three.js.
 *
 * Honors prefers-reduced-motion (single static frame) and WebGL
 * failure (null returned; caller falls back to CSS aurora).
 * Always cleans up GPU resources on dispose.
 */
import * as THREE from 'three'

export interface NeuralHandles {
  setScrollProgress: (p: number) => void
  dispose: () => void
}

const VIOLET = new THREE.Color('#8b7cf6')
const CYAN = new THREE.Color('#38d9e8')
const MAGENTA = new THREE.Color('#ff5c87')

export function initNeuralScene(canvas: HTMLCanvasElement): NeuralHandles | null {
  try {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const isCoarse = window.matchMedia('(pointer: coarse)').matches

    const renderer = new THREE.WebGLRenderer({
      canvas, alpha: true, antialias: true, powerPreference: 'low-power',
    })
    const dpr = Math.min(window.devicePixelRatio || 1, isCoarse ? 1.25 : 1.75)
    renderer.setPixelRatio(dpr)

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(46, 1, 0.1, 100)
    camera.position.set(0, 0.2, 7.2)

    const group = new THREE.Group()
    scene.add(group)

    /* ---------- shared sprite mask ---------- */
    const dotTex = makeDotTexture()

    /* ---------- particle nebula: clustered spherical shell ---------- */
    const N = isCoarse ? 900 : 1700
    const positions = new Float32Array(N * 3)
    const colors = new Float32Array(N * 3)
    const sizes = new Float32Array(N)
    const seeds = new Float32Array(N)
    for (let i = 0; i < N; i++) {
      // fuzz + gentle ripples through the shell so the silhouette breathes
      const radius = 2.5 + (Math.random() - 0.5) * 0.9 + 0.35 * Math.sin(i * 0.31)
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta) * 1.12
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta) * 0.88
      positions[i * 3 + 2] = radius * Math.cos(phi)
      const t = Math.random()
      const c = t < 0.6
        ? VIOLET.clone().lerp(CYAN, Math.random() * 0.45)
        : t < 0.85
          ? CYAN.clone().lerp(VIOLET, Math.random() * 0.4)
          : MAGENTA.clone().lerp(VIOLET, Math.random() * 0.6)
      c.multiplyScalar(0.75 + Math.random() * 0.45)
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b
      sizes[i] = Math.random() < 0.05 ? 16 + Math.random() * 12 : 4 + Math.random() * 9
      seeds[i] = Math.random() * Math.PI * 2
    }
    const pgeo = new THREE.BufferGeometry()
    pgeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    pgeo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    pgeo.setAttribute('size', new THREE.BufferAttribute(sizes, 1))
    pgeo.setAttribute('seed', new THREE.BufferAttribute(seeds, 1))

    const pmat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      vertexColors: true,
      uniforms: { uTex: { value: dotTex }, uTime: { value: 0 } },
      vertexShader: `
        attribute float size;
        attribute float seed;
        uniform float uTime;
        varying vec3 vColor;
        varying float vTwinkle;
        void main() {
          vColor = color;
          vec3 p = position;
          float w = 0.12;
          p.x += w * sin(uTime * 0.6 + seed);
          p.y += w * sin(uTime * 0.47 + seed * 1.7);
          p.z += w * sin(uTime * 0.53 + seed * 2.3);
          vTwinkle = 0.55 + 0.45 * sin(uTime * 1.4 + seed * 3.1);
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_PointSize = size * (7.2 / -mv.z); // size attenuation: depth before decoration
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: `
        uniform sampler2D uTex;
        varying vec3 vColor;
        varying float vTwinkle;
        void main() {
          float a = texture2D(uTex, gl_PointCoord).a;
          if (a < 0.02) discard;
          gl_FragColor = vec4(vColor * vTwinkle, a * 0.62);
        }`,
    })
    const points = new THREE.Points(pgeo, pmat)
    group.add(points)

    /* ---------- filaments: web of near-neighbour links ---------- */
    const FIL = isCoarse ? 160 : 320
    const fpos = new Float32Array(FIL * 6)
    const fcol = new Float32Array(FIL * 6)
    for (let i = 0; i < FIL; i++) {
      const a = Math.floor(Math.random() * N)
      let b = Math.floor(Math.random() * N)
      const dist = (j: number, k: number) => {
        const dx = positions[j * 3] - positions[k * 3]
        const dy = positions[j * 3 + 1] - positions[k * 3 + 1]
        const dz = positions[j * 3 + 2] - positions[k * 3 + 2]
        return dx * dx + dy * dy + dz * dz
      }
      let guard = 0
      while (dist(a, b) > 2.2 && guard++ < 24) b = Math.floor(Math.random() * N)
      const c = (Math.random() < 0.7 ? VIOLET : CYAN).clone().multiplyScalar(0.2 + Math.random() * 0.26)
      fpos.set([
        positions[a * 3], positions[a * 3 + 1], positions[a * 3 + 2],
        positions[b * 3], positions[b * 3 + 1], positions[b * 3 + 2],
      ], i * 6)
      fcol.set([c.r, c.g, c.b, c.r, c.g, c.b], i * 6)
    }
    const fgeo = new THREE.BufferGeometry()
    fgeo.setAttribute('position', new THREE.BufferAttribute(fpos, 3))
    fgeo.setAttribute('color', new THREE.BufferAttribute(fcol, 3))
    const fmat = new THREE.LineBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.17,
      blending: THREE.AdditiveBlending, depthWrite: false,
    })
    group.add(new THREE.LineSegments(fgeo, fmat))

    /* ---------- anomaly cores: three pulsing signature points ---------- */
    const anomalies = [
      { pos: new THREE.Vector3(-1.9, 1.35, 0.7), color: MAGENTA, phase: 0 },
      { pos: new THREE.Vector3(1.7, -1.5, 0.4), color: VIOLET, phase: 2.1 },
      { pos: new THREE.Vector3(0.9, 0.4, -1.4), color: CYAN, phase: 4.2 },
    ]
    const cores = anomalies.map((s) => {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.9, 1.04, 64),
        new THREE.MeshBasicMaterial({
          color: s.color, transparent: true, opacity: 0,
          blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide,
        }),
      )
      ring.position.copy(s.pos)
      ring.scale.setScalar(0.35)
      group.add(ring)
      return { spot: s, ring }
    })
    for (const c of anomalies) {
      // bright nucleus halo behind each anomaly (static)
      const nuc = new THREE.Mesh(
        new THREE.CircleGeometry(0.4, 32),
        new THREE.MeshBasicMaterial({
          color: c.color, transparent: true, opacity: 0.13,
          blending: THREE.AdditiveBlending, depthWrite: false,
        }),
      )
      nuc.position.copy(c.pos)
      nuc.scale.setScalar(1.7)
      group.add(nuc)
    }

    /* ---------- data streams: sparse fast particles through the structure --- */
    const S = isCoarse ? 90 : 170
    const spos = new Float32Array(S * 3)
    const scol = new Float32Array(S * 3)
    const streams = new THREE.BufferGeometry()
    const streamState: { r: number; a0: number; v: number; y: number; c: THREE.Color }[] = []
    for (let i = 0; i < S; i++) {
      streamState.push({
        r: 2.4 + Math.random() * 1.7,
        a0: Math.random() * Math.PI * 2,
        v: 0.25 + Math.random() * 0.55,
        y: (Math.random() - 0.5) * 1.6,
        c: (Math.random() < 0.5 ? CYAN : VIOLET).clone().multiplyScalar(0.9),
      })
    }
    streams.setAttribute('position', new THREE.BufferAttribute(spos, 3))
    streams.setAttribute('color', new THREE.BufferAttribute(scol, 3))
    const smat = new THREE.PointsMaterial({
      size: 2.4, vertexColors: true, transparent: true, opacity: 0.6,
      blending: THREE.AdditiveBlending, depthWrite: false, map: dotTex, alphaTest: 0.02,
    })
    group.add(new THREE.Points(streams, smat))

    /* ---------- ambient evidence-trail arc ---------- */
    const arcPts: THREE.Vector3[] = []
    for (let i = 0; i <= 60; i++) {
      const t = i / 60
      arcPts.push(new THREE.Vector3(
        Math.cos(t * Math.PI * 1.6) * 3.6,
        -0.4 + Math.sin(t * Math.PI * 2.2) * 0.5 + t * 0.8,
        Math.sin(t * Math.PI * 1.6) * 2.6,
      ))
    }
    const arcGeo = new THREE.BufferGeometry().setFromPoints(arcPts)
    group.add(new THREE.Line(arcGeo, new THREE.LineBasicMaterial({
      color: VIOLET, transparent: true, opacity: 0.09, blending: THREE.AdditiveBlending,
    })))

    /* ---------- interaction state ---------- */
    let scrollP = 0
    let targetRX = 0, targetRY = 0, curRX = 0, curRY = 0
    let camX = 0, camY = 0.2
    let running = true
    let lastT = performance.now()

    function onPointer(e: PointerEvent) {
      const nx = (e.clientX / window.innerWidth) * 2 - 1
      const ny = (e.clientY / window.innerHeight) * 2 - 1
      targetRY = nx * 0.32
      targetRX = ny * 0.2
      camX = -nx * 0.35
    }
    if (!isCoarse) window.addEventListener('pointermove', onPointer, { passive: true })
    function onVisibility() { running = !document.hidden }
    document.addEventListener('visibilitychange', onVisibility)

    function loopDriftY(base: number, p: number) {
      return base + p * 0.35 + p * p * 0.4
    }

    function frame(now: number) {
      rafId = requestAnimationFrame(frame)
      if (!running) return
      const dt = Math.min((now - lastT) / 1000, 0.05)
      lastT = now
      const t = now / 1000

      // continuous slow spin + pointer-eased parallax
      group.rotation.y += dt * (0.1 + scrollP * 0.16)
      curRY += (targetRY - curRY) * 0.045
      curRX += (targetRX - curRX) * 0.045
      group.rotation.y += curRY * dt * 2.4
      group.rotation.x = curRX * 0.8 + Math.sin(t * 0.23) * 0.06

      camY = 0.2 + loopDriftY(0, scrollP)
      camera.position.x += (camX - camera.position.x) * 0.05
      camera.position.y += (camY - camera.position.y) * 0.05
      camera.position.z = 7.2 - scrollP * 1.15
      camera.lookAt(0, 0, 0)

      pmat.uniforms.uTime.value = t
      group.position.y = Math.sin(t * 0.35) * 0.12 * (1 - scrollP) + scrollP * 0.2

      for (const c of cores) {
        const ph = (t * 0.9 + c.spot.phase) % (Math.PI * 2)
        const wave = Math.max(0, Math.sin(ph)) ** 3
        const mat = c.ring.material as THREE.MeshBasicMaterial
        mat.opacity = wave * 0.34
        c.ring.scale.setScalar(0.3 + wave * 1.15)
        c.ring.lookAt(camera.position)
      }

      for (let i = 0; i < S; i++) {
        const s = streamState[i]
        const a = s.a0 + t * s.v
        spos[i * 3] = Math.cos(a) * s.r
        spos[i * 3 + 1] = s.y + Math.sin(a * 2 + i) * 0.25
        spos[i * 3 + 2] = Math.sin(a) * s.r
        scol[i * 3] = s.c.r; scol[i * 3 + 1] = s.c.g; scol[i * 3 + 2] = s.c.b
      }
      const sa = streams.attributes.position as THREE.BufferAttribute
      const sca = streams.attributes.color as THREE.BufferAttribute
      sa.needsUpdate = true; sca.needsUpdate = true

      fmat.opacity = 0.13 + 0.05 * Math.sin(t * 0.8) + scrollP * 0.06

      renderer.render(scene, camera)
    }
    let rafId = requestAnimationFrame(frame)

    function size() {
      const w = canvas.clientWidth || 800
      const h = canvas.clientHeight || 600
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    size()
    const ro = new ResizeObserver(size)
    if (canvas.parentElement) ro.observe(canvas.parentElement)
    if (canvas.parentElement) {
      // full stage placement handled by CSS; this keeps the buffer matched
      ro.observe(document.body)
    }

    function dispose() {
      cancelAnimationFrame(rafId)
      window.removeEventListener('pointermove', onPointer)
      document.removeEventListener('visibilitychange', onVisibility)
      ro.disconnect()
      pgeo.dispose(); fgeo.dispose(); streams.dispose(); arcGeo.dispose()
      pmat.dispose(); fmat.dispose(); smat.dispose(); dotTex.dispose()
      for (const c of cores) {
        (c.ring.material as THREE.Material).dispose()
        c.ring.geometry.dispose()
      }
      renderer.dispose()
    }

    /* reduced motion: one static frame, no animation loop */
    if (reducedMotion) {
      cancelAnimationFrame(rafId)
      lastT = performance.now()
      pmat.uniforms.uTime.value = 3.3
      fmat.opacity = 0.3
      renderer.render(scene, camera)
      return { setScrollProgress: () => { /* static frame */ }, dispose }
    }

    return { setScrollProgress: (p) => { scrollP = Math.max(0, Math.min(1, p)) }, dispose }
  } catch {
    /* WebGL unavailable — caller falls back to CSS aurora */
    return null
  }
}

/* ---------- texture helpers ---------- */
function makeDotTexture(): THREE.Texture {
  const s = 64
  const cv = document.createElement('canvas')
  cv.width = cv.height = s
  const g = cv.getContext('2d')!
  const grad = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2)
  grad.addColorStop(0, 'rgba(255,255,255,1)')
  grad.addColorStop(0.35, 'rgba(255,255,255,0.5)')
  grad.addColorStop(1, 'rgba(255,255,255,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, s, s)
  const tex = new THREE.CanvasTexture(cv)
  tex.needsUpdate = true
  return tex
}
