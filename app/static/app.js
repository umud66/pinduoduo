(async () => {
  const title = document.querySelector('#status-title');
  const output = document.querySelector('#status-json');
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    title.textContent = data.ok ? '本地服务运行正常' : '服务状态异常';
    output.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    title.textContent = '无法连接本地服务';
    output.textContent = String(error);
  }
})();
