document.getElementById('load-content').addEventListener('click', function () {
  // Load dynamic content from an API or a local data source
  // This is a placeholder for the actual content loading process
  const content = 'This is some dynamic content.'

  // Insert the dynamic content into the content section
  // (textContent — never innerHTML — for anything that could come from an API)
  document.getElementById('content').textContent = content
})
