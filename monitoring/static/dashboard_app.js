/* ===========================================================================
   Vijay's Agent -- Dashboard JavaScript
   Three.js particle background + live data + 3D tilt effects
   =========================================================================== */

// ========== THREE.JS PARTICLE BACKGROUND ==========
function initParticleBackground() {
    const canvas = document.getElementById('three-bg');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Create particles
    const particleCount = 200;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const velocities = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
        positions[i] = (Math.random() - 0.5) * 30;
        positions[i + 1] = (Math.random() - 0.5) * 30;
        positions[i + 2] = (Math.random() - 0.5) * 15;
        velocities[i] = (Math.random() - 0.5) * 0.003;
        velocities[i + 1] = (Math.random() - 0.5) * 0.003;
        velocities[i + 2] = (Math.random() - 0.5) * 0.001;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
        size: 0.03,
        color: 0x22d3ee,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // Connection lines
    const lineMaterial = new THREE.LineBasicMaterial({
        color: 0x3b82f6,
        transparent: true,
        opacity: 0.06,
    });

    camera.position.z = 8;

    // Mouse tracking for subtle parallax
    let mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX / window.innerWidth - 0.5) * 0.5;
        mouseY = (e.clientY / window.innerHeight - 0.5) * 0.5;
    });

    function animate() {
        requestAnimationFrame(animate);

        const pos = geometry.attributes.position.array;
        for (let i = 0; i < particleCount * 3; i += 3) {
            pos[i] += velocities[i];
            pos[i + 1] += velocities[i + 1];
            pos[i + 2] += velocities[i + 2];

            // Wrap around
            if (pos[i] > 15) pos[i] = -15;
            if (pos[i] < -15) pos[i] = 15;
            if (pos[i + 1] > 15) pos[i + 1] = -15;
            if (pos[i + 1] < -15) pos[i + 1] = 15;
        }
        geometry.attributes.position.needsUpdate = true;

        particles.rotation.y += 0.0003;
        particles.rotation.x += 0.0001;

        // Subtle camera parallax
        camera.position.x += (mouseX - camera.position.x) * 0.02;
        camera.position.y += (-mouseY - camera.position.y) * 0.02;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    }

    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}


// ========== 3D TILT EFFECT ON CARDS ==========
function initTiltCards() {
    document.querySelectorAll('.tilt-card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = (y - centerY) / centerY * -4;
            const rotateY = (x - centerX) / centerX * 4;
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
        });
    });
}


// ========== SMOOTH COUNTER ANIMATION ==========
function animateCounter(element, target, duration = 1000) {
    const start = parseFloat(element.textContent) || 0;
    const startTime = performance.now();
    const isFloat = target % 1 !== 0;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // Ease out cubic
        const current = start + (target - start) * eased;

        element.textContent = isFloat ? current.toFixed(2) : Math.round(current);

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}


// ========== LIVE DATA FETCHING ==========
let previousData = null;

async function fetchDashboardData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        updateDashboard(data);
        previousData = data;
    } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
    }
}

function updateDashboard(data) {
    // Update server clock
    const clockEl = document.getElementById('server-clock');
    if (clockEl) clockEl.textContent = data.server_time;

    // Update KPIs with animation
    updateKPI('kpi-total', data.stats.total_decisions);
    updateKPI('kpi-executed', data.stats.executed_trades);
    updateKPI('kpi-grounding', data.stats.avg_grounding_score);
    updateKPI('kpi-debates', data.stats.debates_completed);

    // Update decisions table
    updateDecisionsTable(data.decisions);

    // Update debate panel
    updateDebatePanel(data.debate);

    // Update RAG status
    updateRAGStatus(data.stats);

    // Update system status
    updateSystemStatus(data.stats);
}

function updateKPI(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    const currentVal = parseFloat(el.textContent) || 0;
    if (currentVal !== value) {
        animateCounter(el, value);
    }
}

function updateDecisionsTable(decisions) {
    const tbody = document.getElementById('decisions-body');
    if (!tbody) return;

    if (!decisions || decisions.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="7" class="empty-state">
                <div class="empty-icon">--</div>
                Waiting for first trading cycle...
            </td></tr>`;
        return;
    }

    tbody.innerHTML = decisions.map((d, i) => {
        const actionClass = d.action === 'BUY' ? 'action-buy'
            : d.action === 'SELL' ? 'action-sell' : 'action-hold';

        const scoreClass = d.grounding_score >= 0.7 ? 'score-high'
            : d.grounding_score >= 0.4 ? 'score-mid' : 'score-low';

        const scoreWidth = Math.round(d.grounding_score * 100);

        const ragText = d.rag_sources && d.rag_sources.length > 0
            ? d.rag_sources.join(', ') : '<span style="color:var(--text-muted)">none</span>';

        return `
            <tr style="animation-delay: ${i * 0.03}s">
                <td>${d.time.split(' ')[1] || d.time}</td>
                <td style="color: var(--accent-cyan); font-weight: 600;">${d.pair}</td>
                <td><span class="action-badge ${actionClass}">${d.action}</span></td>
                <td>${d.confidence}%</td>
                <td>
                    <div class="score-bar-wrapper">
                        <div class="score-bar">
                            <div class="score-bar-fill ${scoreClass}" style="width: ${scoreWidth}%"></div>
                        </div>
                        <span>${d.grounding_score}</span>
                    </div>
                </td>
                <td style="font-size: 0.65rem;">${ragText}</td>
                <td class="outcome-text">${formatOutcome(d.outcome)}</td>
            </tr>`;
    }).join('');
}

function formatOutcome(outcome) {
    if (!outcome) return '';
    if (outcome.includes('VETOED') || outcome.includes('OVERRIDE'))
        return `<span style="color: var(--accent-red);">${outcome}</span>`;
    if (outcome.includes('EXECUTED'))
        return `<span style="color: var(--accent-green);">${outcome}</span>`;
    if (outcome.includes('HOLD'))
        return `<span style="color: var(--accent-yellow);">${outcome}</span>`;
    return outcome;
}

function updateDebatePanel(debate) {
    const container = document.getElementById('debate-content');
    if (!container) return;

    if (!debate) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">--</div>
                No debate data yet. Waiting for first Gold analysis cycle...
            </div>`;
        return;
    }

    let html = '';

    // Round 1 - Independent decisions
    html += '<div class="debate-round-title">Round 1 -- Independent Analysis</div>';
    if (debate.round1_decisions) {
        Object.entries(debate.round1_decisions).forEach(([model, decision]) => {
            const action = decision.action || '?';
            const conf = decision.confidence || 0;
            const strategy = decision.strategy_used || '?';
            const actionClass = action === 'BUY' ? 'action-buy'
                : action === 'SELL' ? 'action-sell' : 'action-hold';

            html += `
                <div class="debate-model-row">
                    <span class="model-name">${model.substring(0, 25)}</span>
                    <span class="action-badge ${actionClass}">${action}</span>
                    <span style="color: var(--text-secondary); font-size: 0.7rem;">${conf}% | ${strategy}</span>
                </div>`;
        });
    }

    // Vote tally
    if (debate.vote_tally && Object.keys(debate.vote_tally).length > 0) {
        html += '<div class="debate-round-title">Round 3 -- Consensus Vote</div>';
        html += '<div class="vote-bar-container">';
        Object.entries(debate.vote_tally).forEach(([action, count]) => {
            const voteClass = action === 'BUY' ? 'vote-buy'
                : action === 'SELL' ? 'vote-sell' : 'vote-hold';
            html += `<div class="vote-bar ${voteClass}">${action}: ${count}</div>`;
        });
        html += '</div>';
    }

    // Consensus
    const consColor = debate.consensus_action === 'BUY' ? 'var(--accent-green)'
        : debate.consensus_action === 'SELL' ? 'var(--accent-red)' : 'var(--accent-yellow)';

    html += `
        <div class="consensus-display">
            <div class="consensus-label">Consensus</div>
            <div class="consensus-value" style="color: ${consColor};">
                ${debate.consensus_action} (${debate.consensus_confidence}%)
            </div>
        </div>`;

    if (debate.timestamp) {
        html += `<div style="text-align: center; margin-top: 0.5rem; font-size: 0.65rem; color: var(--text-muted);">Last debate: ${debate.timestamp}</div>`;
    }

    container.innerHTML = html;
}

function updateRAGStatus(stats) {
    const el = document.getElementById('rag-content');
    if (!el) return;

    const scoreColor = stats.avg_grounding_score >= 0.7 ? 'var(--accent-green)'
        : stats.avg_grounding_score >= 0.4 ? 'var(--accent-yellow)' : 'var(--accent-red)';

    const scorePercent = Math.round(stats.avg_grounding_score * 100);

    el.innerHTML = `
        <div class="progress-container">
            <div class="progress-label">Avg Grounding Score</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${scorePercent}%; background: linear-gradient(90deg, ${scoreColor}, var(--accent-blue));"></div>
            </div>
            <div style="text-align: right; margin-top: 0.25rem; font-family: var(--font-mono); font-size: 0.75rem; color: ${scoreColor};">${stats.avg_grounding_score.toFixed(3)} / 1.000</div>
        </div>

        <div class="stat-row">
            <span class="stat-label">Grounded Decisions</span>
            <span class="stat-value" style="color: var(--accent-green);">${stats.total_decisions}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Risk Vetoes</span>
            <span class="stat-value" style="color: var(--accent-red);">${stats.vetoed}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Unique RAG Sources</span>
            <span class="stat-value" style="color: var(--accent-cyan);">${stats.unique_rag_sources}</span>
        </div>
    `;
}

function updateSystemStatus(stats) {
    const el = document.getElementById('system-content');
    if (!el) return;

    const providerTags = stats.active_providers.map(p =>
        `<span class="provider-tag">${p}</span>`
    ).join('');

    const debateModelTags = stats.debate_models.map(m =>
        `<span class="provider-tag">${m}</span>`
    ).join('');

    el.innerHTML = `
        <div class="system-online">
            <div class="status-dot"></div>
            System Online
        </div>

        <div class="stat-row">
            <span class="stat-label">Executed Trades</span>
            <span class="stat-value" style="color: var(--accent-green);">${stats.executed_trades}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Hold Decisions</span>
            <span class="stat-value" style="color: var(--accent-yellow);">${stats.holds}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Debates Completed</span>
            <span class="stat-value" style="color: var(--accent-cyan);">${stats.debates_completed}</span>
        </div>

        <div style="margin-top: 1rem;">
            <div class="progress-label" style="margin-bottom: 0.5rem;">Risk Rules</div>
            <div class="risk-rule">Max 2-3 trades/day</div>
            <div class="risk-rule">2% risk per trade</div>
            <div class="risk-rule">5% max drawdown</div>
            <div class="risk-rule">Min 1.5 R:R ratio</div>
        </div>

        <div class="providers-list">
            <div class="progress-label" style="margin-bottom: 0.5rem;">Active Providers</div>
            ${providerTags || '<span style="color: var(--text-muted);">N/A</span>'}
        </div>

        <div class="providers-list">
            <div class="progress-label" style="margin-bottom: 0.5rem;">Debate Models</div>
            ${debateModelTags || '<span style="color: var(--text-muted);">N/A</span>'}
        </div>
    `;
}


// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
    initParticleBackground();
    initTiltCards();
    fetchDashboardData();

    // Live refresh every 5 seconds
    setInterval(fetchDashboardData, 5000);
});
