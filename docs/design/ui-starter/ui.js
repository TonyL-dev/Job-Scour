/* Local example interactions only. No persistence, network or application dependencies. */
document.querySelectorAll('[data-tabs]').forEach(container => {
  const tabs = [...container.querySelectorAll('[role="tab"]')]
  function select(index, focus) {
    tabs.forEach((tab, i) => {
      tab.setAttribute('aria-selected', String(i === index))
      tab.tabIndex = i === index ? 0 : -1
      document.getElementById(tab.getAttribute('aria-controls')).hidden = i !== index
    })
    if (focus) tabs[index].focus()
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => select(index, false))
    tab.addEventListener('keydown', event => {
      const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index - 1 + tabs.length) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : undefined
      if (next !== undefined) { event.preventDefault(); select(next, true) }
    })
  })
})
document.querySelectorAll('details.disclosure').forEach(disclosure => {
  disclosure.addEventListener('keydown', event => {
    if (event.key === 'Escape' && disclosure.open) {
      event.stopPropagation(); disclosure.open = false; disclosure.querySelector('summary').focus()
    }
  })
})
document.querySelector('[data-demo-form]').addEventListener('submit', event => {
  event.preventDefault()
  document.querySelector('[data-save-status]').textContent = 'Example saved in this page only. No server request was made.'
})
