// Léptethető ábrák. Egy .stepper elem tartalmaz egy SVG-t, amiben az elemek
// data-step="N" attribútumot kapnak (N-edik lépéstől látszanak), vagy
// data-only="N,M" attribútumot (csak ezekben a lépésekben látszanak).
// A lépések szövegei a stepper data-captions attribútumában, "|" jellel
// elválasztva vannak.

document.querySelectorAll('.stepper').forEach((root) => {
  const captions = (root.dataset.captions || '').split('|').map((s) => s.trim())
  const total = captions.length
  const caption = root.querySelector('.caption')
  const counter = root.querySelector('.counter')
  const prev = root.querySelector('[data-prev]')
  const next = root.querySelector('[data-next]')
  const reset = root.querySelector('[data-reset]')
  let step = 0

  function render() {
    root.querySelectorAll('[data-step]').forEach((el) => {
      const visible = Number(el.dataset.step) <= step
      el.classList.toggle('step-hidden', !visible)
      el.classList.toggle('step-shown', visible)
    })
    root.querySelectorAll('[data-only]').forEach((el) => {
      const steps = el.dataset.only.split(',').map(Number)
      const visible = steps.includes(step)
      el.style.display = visible ? '' : 'none'
    })
    caption.innerHTML = captions[step] || ''
    counter.textContent = `${step + 1} / ${total}`
    prev.disabled = step === 0
    next.disabled = step === total - 1
  }

  prev.addEventListener('click', () => { step = Math.max(0, step - 1); render() })
  next.addEventListener('click', () => { step = Math.min(total - 1, step + 1); render() })
  if (reset) reset.addEventListener('click', () => { step = 0; render() })
  render()
})

// Kétállású kapcsolós ábrák: .toggle-figure, benne gombok data-state="x"
// értékkel, és elemek data-when="x" attribútummal.
document.querySelectorAll('.toggle-figure').forEach((root) => {
  const buttons = root.querySelectorAll('.toggle button')
  const captionEl = root.querySelector('.caption')

  function set(state) {
    buttons.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.state === state)))
    root.querySelectorAll('[data-when]').forEach((el) => {
      el.style.display = el.dataset.when.split(',').includes(state) ? '' : 'none'
    })
    const active = root.querySelector(`.toggle button[data-state="${state}"]`)
    if (captionEl && active) captionEl.innerHTML = active.dataset.caption || ''
  }

  buttons.forEach((b) => b.addEventListener('click', () => set(b.dataset.state)))
  set(buttons[0].dataset.state)
})

// Haladás az index oldalon (csak a saját böngésződben tárolódik).
document.querySelectorAll('input[data-progress]').forEach((box) => {
  const key = `tananyag:${box.dataset.progress}`
  try { box.checked = localStorage.getItem(key) === '1' } catch { /* nem elérhető */ }
  box.addEventListener('change', () => {
    try { localStorage.setItem(key, box.checked ? '1' : '0') } catch { /* nem elérhető */ }
  })
})
