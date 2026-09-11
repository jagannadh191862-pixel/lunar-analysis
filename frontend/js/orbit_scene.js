/**
 * Lunar Correspondence AI — 4K Photorealistic 3D Moon & Chandrayaan-2 Spacecraft
 * Built with Three.js (WebGL Hardware Accelerated):
 * - 4K NASA LROC Diffuse & Topographic Bump Normal Mapping (4096x2048)
 * - Directional Sun lighting with razor-sharp terminator line and Earthshine
 * - Photorealistic 3D Chandrayaan-2 Orbiter: Gold MLI foil bus, articulated solar wings,
 *   steerable parabolic dish antenna, optical camera lenses (TMC-2 & OHRC), and active laser scanner
 * - Complete starry cosmos with distant 3D planets (Earth, Mars, Jupiter, Saturn)
 */

export class OrbitScene {
  constructor(canvasId, hudElements = {}) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.hud = hudElements;

    // Ephemeris Telemetry (Chandrayaan-2 100km polar orbit)
    this.altitudeKm = 100.4;
    this.velocityKmS = 1.633;
    this.orbitPeriodMin = 118.2;
    this.inclinationDeg = 90.1;

    // Orbital State
    this.trueAnomalyRad = 1.0;
    this.orbitSpeed = 0.0032;
    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    this.initThree();
    this.setupCosmos();
    this.setupPlanets();
    this.setupMoon();
    this.setupChandrayaan2();
    this.setupLighting();

    this.onResize();
    window.addEventListener('resize', () => this.onResize());
    window.addEventListener('mousemove', (e) => this.onMouseMove(e));

    this.isRunning = true;
    this.animate();
  }

  initThree() {
    const THREE = window.THREE;
    if (!THREE) {
      console.error('Three.js not found');
      return;
    }

    // 1. WebGL Renderer with High Dynamic Range and Tone Mapping
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // 2. Scene
    this.scene = new THREE.Scene();

    // 3. Cinematic Aerospace Camera
    const aspect = this.canvas.clientWidth / this.canvas.clientHeight || 1;
    this.camera = new THREE.PerspectiveCamera(36, aspect, 0.1, 2000);
    this.camera.position.set(0, 0, 36);
  }

  setupCosmos() {
    const THREE = window.THREE;
    // 1,200 Multi-temperature starfield particles
    const starCount = 1200;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(starCount * 3);
    const colors = new Float32Array(starCount * 3);

    const palette = [
      new THREE.Color(0xffffff), // Pure white
      new THREE.Color(0xe0f2fe), // Blue-white
      new THREE.Color(0xfef08a), // Solar yellow
      new THREE.Color(0xfed7aa), // Amber
      new THREE.Color(0x93c5fd), // Cyan-blue
    ];

    for (let i = 0; i < starCount; i++) {
      // Distribute stars on outer celestial sphere
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      const r = 380 + Math.random() * 120;

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);

      const col = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = col.r;
      colors[i * 3 + 1] = col.g;
      colors[i * 3 + 2] = col.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 1.6,
      vertexColors: true,
      transparent: true,
      opacity: 0.88,
      sizeAttenuation: true
    });

    this.starField = new THREE.Points(geometry, material);
    this.scene.add(this.starField);
  }

  setupPlanets() {
    const THREE = window.THREE;
    this.planetsGroup = new THREE.Group();

    // 1. Distant Earth ("The Blue Marble")
    const earthGeo = new THREE.SphereGeometry(1.6, 32, 32);
    const earthMat = new THREE.MeshStandardMaterial({
      color: 0x1d4ed8,
      roughness: 0.6,
      metalness: 0.1,
    });
    this.earth = new THREE.Mesh(earthGeo, earthMat);
    this.earth.position.set(-22, 11, -45);
    this.planetsGroup.add(this.earth);

    // Earth Atmospheric Rayleigh Limb Glow
    const earthAtmGeo = new THREE.SphereGeometry(1.72, 32, 32);
    const earthAtmMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.35,
      side: THREE.BackSide
    });
    const earthAtm = new THREE.Mesh(earthAtmGeo, earthAtmMat);
    this.earth.add(earthAtm);

    // 2. Mars ("The Red Planet")
    const marsGeo = new THREE.SphereGeometry(0.85, 32, 32);
    const marsMat = new THREE.MeshStandardMaterial({
      color: 0xc2410c,
      roughness: 0.8,
      metalness: 0.05
    });
    this.mars = new THREE.Mesh(marsGeo, marsMat);
    this.mars.position.set(-28, -12, -50);
    this.planetsGroup.add(this.mars);

    // 3. Jupiter (Banded Gas Giant)
    const jupGeo = new THREE.SphereGeometry(1.4, 32, 32);
    const jupMat = new THREE.MeshStandardMaterial({
      color: 0xd97706,
      roughness: 0.7,
      metalness: 0.05
    });
    this.jupiter = new THREE.Mesh(jupGeo, jupMat);
    this.jupiter.position.set(-8, 14, -60);
    this.planetsGroup.add(this.jupiter);

    // 4. Saturn with Tilted Rings
    const satGeo = new THREE.SphereGeometry(1.1, 32, 32);
    const satMat = new THREE.MeshStandardMaterial({
      color: 0xfef08a,
      roughness: 0.7,
      metalness: 0.05
    });
    this.saturn = new THREE.Mesh(satGeo, satMat);
    this.saturn.position.set(24, 15, -65);

    // Saturn Ring System
    const ringGeo = new THREE.RingGeometry(1.5, 2.8, 48);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0xfde047,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.65
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI * 0.42;
    ringMesh.rotation.y = 0.2;
    this.saturn.add(ringMesh);
    this.planetsGroup.add(this.saturn);

    this.scene.add(this.planetsGroup);
  }

  setupMoon() {
    const THREE = window.THREE;
    this.moonGroup = new THREE.Group();

    // High-resolution sphere: radius 8.5 units, 128x128 segments
    const geometry = new THREE.SphereGeometry(8.5, 128, 128);

    // Load 4K Diffuse and Bump Textures
    const textureLoader = new THREE.TextureLoader();
    const diffuseMap = textureLoader.load('assets/textures/moon_diffuse_4k.jpg');
    const bumpMap = textureLoader.load('assets/textures/moon_bump_4k.jpg');

    diffuseMap.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
    bumpMap.anisotropy = this.renderer.capabilities.getMaxAnisotropy();

    // Realistic Lunar Surface Material: Regolith High Diffuse + Normal Relief
    const material = new THREE.MeshStandardMaterial({
      map: diffuseMap,
      bumpMap: bumpMap,
      bumpScale: 0.16,
      roughness: 0.95,
      metalness: 0.04,
    });

    this.moonMesh = new THREE.Mesh(geometry, material);
    this.moonMesh.castShadow = true;
    this.moonMesh.receiveShadow = true;
    this.moonGroup.add(this.moonMesh);

    // Subtle Lunar Atmospheric/Diffractive Horizon Limb Glow
    const limbGeo = new THREE.SphereGeometry(8.58, 64, 64);
    const limbMat = new THREE.MeshBasicMaterial({
      color: 0x93c5fd,
      transparent: true,
      opacity: 0.12,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending
    });
    const limbMesh = new THREE.Mesh(limbGeo, limbMat);
    this.moonGroup.add(limbMesh);

    // Position Moon toward right side of hero viewport
    this.moonGroup.position.set(7.5, 0, 0);
    this.scene.add(this.moonGroup);
  }

  setupChandrayaan2() {
    const THREE = window.THREE;
    this.satellite = new THREE.Group();

    const textureLoader = new THREE.TextureLoader();
    const goldMliTex = textureLoader.load('assets/textures/satellite_gold_mli.jpg');
    const solarTex = textureLoader.load('assets/textures/satellite_solar_panel.jpg');

    // 1. Central Spacecraft Bus (Gold MLI Thermal Insulation)
    const busGeo = new THREE.BoxGeometry(0.7, 0.7, 0.85);
    const busMat = new THREE.MeshStandardMaterial({
      map: goldMliTex,
      color: 0xf59e0b,
      metalness: 0.88,
      roughness: 0.28,
    });
    const busMesh = new THREE.Mesh(busGeo, busMat);
    busMesh.castShadow = true;
    this.satellite.add(busMesh);

    // 2. Twin Articulated Solar Array Wings (Photovoltaic Silicon)
    const panelGeo = new THREE.BoxGeometry(0.12, 1.4, 0.8);
    const panelMat = new THREE.MeshStandardMaterial({
      map: solarTex,
      color: 0x0284c7,
      metalness: 0.65,
      roughness: 0.22,
    });

    // Wing +Y
    this.wing1 = new THREE.Mesh(panelGeo, panelMat);
    this.wing1.position.set(0, 1.15, 0);
    this.satellite.add(this.wing1);

    // Wing -Y
    this.wing2 = new THREE.Mesh(panelGeo, panelMat);
    this.wing2.position.set(0, -1.15, 0);
    this.satellite.add(this.wing2);

    // 3. Steerable High-Gain Parabolic Reflector Antenna (White Carbon Composite)
    const dishGeo = new THREE.SphereGeometry(0.48, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.45);
    const dishMat = new THREE.MeshStandardMaterial({
      color: 0xf8fafc,
      metalness: 0.1,
      roughness: 0.4,
      side: THREE.DoubleSide
    });
    this.dish = new THREE.Mesh(dishGeo, dishMat);
    this.dish.position.set(-0.55, 0, 0);
    this.dish.rotation.y = Math.PI * 0.5;
    this.satellite.add(this.dish);

    // Feed horn boom
    const hornGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.4, 12);
    const hornMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.8 });
    const horn = new THREE.Mesh(hornGeo, hornMat);
    horn.rotation.z = Math.PI * 0.5;
    horn.position.set(-0.75, 0, 0);
    this.satellite.add(horn);

    // 4. Optical Payloads Deck (TMC-2 & OHRC Lenses)
    const lensGeo = new THREE.CylinderGeometry(0.1, 0.12, 0.22, 16);
    const lensMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.95,
      roughness: 0.1
    });

    // TMC-2 Lens
    const tmcLens = new THREE.Mesh(lensGeo, lensMat);
    tmcLens.rotation.z = Math.PI * 0.5;
    tmcLens.position.set(0.46, 0.18, 0.15);
    this.satellite.add(tmcLens);

    // OHRC High-Resolution Lens
    const ohrcLens = new THREE.Mesh(lensGeo, lensMat);
    ohrcLens.rotation.z = Math.PI * 0.5;
    ohrcLens.position.set(0.46, -0.18, 0.15);
    this.satellite.add(ohrcLens);

    // 5. Active Nadir Laser Scanner Cone (Translucent Cyan Beam)
    const beamGeo = new THREE.ConeGeometry(0.65, 4.2, 24, 1, true);
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending
    });
    this.laserBeam = new THREE.Mesh(beamGeo, beamMat);
    this.laserBeam.rotation.z = -Math.PI * 0.5;
    this.laserBeam.position.set(2.4, 0, 0);
    this.satellite.add(this.laserBeam);

    // 6. Surface Laser Reticle Crosshair
    const reticleGeo = new THREE.RingGeometry(0.2, 0.28, 32);
    const reticleMat = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending
    });
    this.reticle = new THREE.Mesh(reticleGeo, reticleMat);
    this.scene.add(this.reticle);

    // 7. Polar Orbit Trajectory Line (Glowing Cyan Ellipse)
    const orbitRadiusA = 12.2;
    const orbitRadiusB = 4.4;
    const curvePoints = [];
    for (let i = 0; i <= 128; i++) {
      const theta = (i / 128) * Math.PI * 2;
      const x = orbitRadiusB * Math.sin(theta);
      const y = orbitRadiusA * Math.cos(theta);
      curvePoints.push(new THREE.Vector3(x, y, 0));
    }
    const orbitGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
    const orbitMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.42,
      linewidth: 1
    });
    this.orbitLine = new THREE.Line(orbitGeo, orbitMat);
    this.orbitLine.rotation.z = -0.22;
    this.orbitLine.position.copy(this.moonGroup.position);
    this.scene.add(this.orbitLine);

    this.scene.add(this.satellite);
  }

  setupLighting() {
    const THREE = window.THREE;
    // 1. Direct Solar Illumination (Directional Sunlight from upper left)
    this.sunLight = new THREE.DirectionalLight(0xfffdf5, 2.6);
    this.sunLight.position.set(-30, 24, 30);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 2048;
    this.sunLight.shadow.mapSize.height = 2048;
    this.scene.add(this.sunLight);

    // 2. Ambient Earthshine (Soft bluish light on the dark lunar nightside)
    this.earthshine = new THREE.AmbientLight(0x1e3a8a, 0.12);
    this.scene.add(this.earthshine);

    // 3. Subtle Rim Light for Celestial Definition
    this.rimLight = new THREE.DirectionalLight(0x38bdf8, 0.35);
    this.rimLight.position.set(20, -10, -15);
    this.scene.add(this.rimLight);
  }

  onResize() {
    if (!this.renderer || !this.camera) return;
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;

    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);

    // Adjust Moon position for mobile vs desktop
    if (w < 768) {
      this.moonGroup.position.set(0, 2, 0);
      this.orbitLine.position.set(0, 2, 0);
    } else {
      this.moonGroup.position.set(7.5, 0, 0);
      this.orbitLine.position.set(7.5, 0, 0);
    }
  }

  onMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      this.mouse.targetX = ((e.clientX - rect.left) / rect.width - 0.5) * 4.0;
      this.mouse.targetY = ((e.clientY - rect.top) / rect.height - 0.5) * 4.0;
    }
  }

  animate() {
    if (!this.isRunning) return;

    // Smooth camera parallax
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.05;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.05;

    this.camera.position.x = this.mouse.x;
    this.camera.position.y = -this.mouse.y;
    this.camera.lookAt(0, 0, 0);

    // Slow lunar axial rotation
    if (this.moonMesh) {
      this.moonMesh.rotation.y += 0.0004;
    }

    // 3D Orbital Mechanics for Chandrayaan-2
    this.trueAnomalyRad = (this.trueAnomalyRad + this.orbitSpeed) % (Math.PI * 2);

    const orbitA = 12.2;
    const orbitB = 4.4;
    const tilt = -0.22;

    const rawX = orbitB * Math.sin(this.trueAnomalyRad);
    const rawY = orbitA * Math.cos(this.trueAnomalyRad);

    const cosT = Math.cos(tilt);
    const sinT = Math.sin(tilt);
    const sx = this.moonGroup.position.x + (rawX * cosT - rawY * sinT);
    const sy = this.moonGroup.position.y + (rawX * sinT + rawY * cosT);
    const sz = rawX * 0.85; // 3D depth relative to Moon center

    if (this.satellite) {
      this.satellite.position.set(sx, sy, sz);

      // Nadir pointing attitude: payload lenses point directly toward Moon center
      const moonCenter = this.moonGroup.position;
      const nadirDir = new window.THREE.Vector3().subVectors(moonCenter, this.satellite.position).normalize();
      
      // Orient satellite body
      this.satellite.lookAt(moonCenter);
      // Rotate 90 deg so lenses (+X) face moon center
      this.satellite.rotateY(-Math.PI * 0.5);

      // Solar arrays track sunlight direction
      if (this.wing1 && this.wing2) {
        this.wing1.rotation.y = this.trueAnomalyRad * 0.5;
        this.wing2.rotation.y = this.trueAnomalyRad * 0.5;
      }

      // Laser beam pulse animation
      if (this.laserBeam) {
        this.laserBeam.material.opacity = 0.18 + Math.sin(performance.now() * 0.006) * 0.08;
      }

      // Project surface laser reticle
      if (this.reticle) {
        const rayDir = nadirDir.clone();
        const surfPos = moonCenter.clone().add(rayDir.clone().multiplyScalar(-8.55));
        this.reticle.position.copy(surfPos);
        this.reticle.lookAt(this.satellite.position);
        this.reticle.visible = (sz >= -1.0); // Only visible on near-side
      }
    }

    // Rotate distant planets slightly
    if (this.planetsGroup) {
      this.planetsGroup.rotation.y += 0.0001;
    }

    this.renderer.render(this.scene, this.camera);
    this.updateHUD();

    requestAnimationFrame(() => this.animate());
  }

  updateHUD() {
    if (!this.hud.altitude) return;

    const latVal = Math.sin(this.trueAnomalyRad) * 90.0;
    const latDeg = Math.abs(latVal).toFixed(2);
    const latHemi = latVal >= 0 ? 'N' : 'S';

    const lonVal = ((this.trueAnomalyRad * 180) / Math.PI + 43.2) % 360 - 180;
    const lonDeg = Math.abs(lonVal).toFixed(2);
    const lonHemi = lonVal >= 0 ? 'E' : 'W';

    const anomalyDeg = ((this.trueAnomalyRad * 180) / Math.PI).toFixed(1);

    if (this.hud.altitude) this.hud.altitude.textContent = `${this.altitudeKm} km`;
    if (this.hud.velocity) this.hud.velocity.textContent = `${this.velocityKmS} km/s`;
    if (this.hud.lat) this.hud.lat.textContent = `${latDeg}° ${latHemi}`;
    if (this.hud.lon) this.hud.lon.textContent = `${lonDeg}° ${lonHemi}`;
    if (this.hud.anomaly) this.hud.anomaly.textContent = `${anomalyDeg}°`;
  }

  destroy() {
    this.isRunning = false;
    if (this.renderer) {
      this.renderer.dispose();
    }
  }
}
