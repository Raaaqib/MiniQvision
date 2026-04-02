const slides = Array.from(document.querySelectorAll('.slide'));
const dotNav = document.getElementById('dotNav');
const slideCounter = document.getElementById('slideCounter');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');

let activeIndex = 0;

function buildDots() {
    slides.forEach((slide, index) => {
        const dot = document.createElement('button');
        dot.className = 'dot';
        dot.type = 'button';
        dot.setAttribute('aria-label', `Go to slide ${index + 1}: ${slide.dataset.title || ''}`.trim());
        dot.addEventListener('click', () => goToSlide(index));
        dotNav.appendChild(dot);
    });
}

function updateUi(index) {
    activeIndex = index;

    slides.forEach((slide, i) => {
        slide.classList.toggle('active', i === index);
    });

    const dots = Array.from(dotNav.querySelectorAll('.dot'));
    dots.forEach((dot, i) => {
        dot.classList.toggle('active', i === index);
    });

    slideCounter.textContent = `${index + 1} / ${slides.length}`;
}

function goToSlide(index) {
    const safeIndex = Math.max(0, Math.min(slides.length - 1, index));
    slides[safeIndex].scrollIntoView({ behavior: 'smooth', block: 'start' });
    updateUi(safeIndex);
}

function observeSlides() {
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const idx = slides.findIndex((s) => s === entry.target);
                    if (idx !== -1) {
                        updateUi(idx);
                    }
                }
            });
        },
        { threshold: 0.55 }
    );

    slides.forEach((slide) => observer.observe(slide));
}

function bindControls() {
    prevBtn.addEventListener('click', () => goToSlide(activeIndex - 1));
    nextBtn.addEventListener('click', () => goToSlide(activeIndex + 1));

    document.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowRight' || event.key === 'PageDown') {
            event.preventDefault();
            goToSlide(activeIndex + 1);
        }

        if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
            event.preventDefault();
            goToSlide(activeIndex - 1);
        }

        if (event.key === 'Home') {
            event.preventDefault();
            goToSlide(0);
        }

        if (event.key === 'End') {
            event.preventDefault();
            goToSlide(slides.length - 1);
        }
    });
}

function setupComputeEstimator() {
    const eventsRange = document.getElementById('eventsRange');
    const eventsLabel = document.getElementById('eventsLabel');
    const continuousValue = document.getElementById('continuousValue');
    const twoStageValue = document.getElementById('twoStageValue');
    const savingsValue = document.getElementById('savingsValue');
    const barContinuous = document.getElementById('barContinuous');
    const barTwoStage = document.getElementById('barTwoStage');

    if (!eventsRange) {
        return;
    }

    const fps = 10;
    const yoloSecondsPerInference = 0.3;
    const averageEventDurationSeconds = 1;

    function render() {
        const eventsPerHour = Number(eventsRange.value);
        eventsLabel.textContent = String(eventsPerHour);

        const continuousGpuSeconds = fps * 3600 * yoloSecondsPerInference;
        const twoStageGpuSeconds = eventsPerHour * averageEventDurationSeconds * yoloSecondsPerInference;

        const reduction = (1 - twoStageGpuSeconds / continuousGpuSeconds) * 100;

        continuousValue.textContent = `${continuousGpuSeconds.toFixed(0)}s GPU/h`;
        twoStageValue.textContent = `${twoStageGpuSeconds.toFixed(1)}s GPU/h`;
        savingsValue.textContent = `${Math.max(0, reduction).toFixed(2)}%`;

        barContinuous.style.width = '100%';
        const normalizedTwoStage = Math.max(2, Math.min(100, (twoStageGpuSeconds / continuousGpuSeconds) * 100));
        barTwoStage.style.width = `${normalizedTwoStage}%`;
    }

    eventsRange.addEventListener('input', render);
    render();
}

buildDots();
bindControls();
observeSlides();
setupComputeEstimator();
updateUi(0);
