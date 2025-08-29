(function () {
  const iframe = document.createElement("iframe");
  iframe.id = "chat-iframe";
  iframe.src = "http://127.0.0.1:9050/";
  iframe.style.cssText = `
    position: fixed;
    bottom: 90px;
    right: 20px;
    width: 400px;
    height: 600px;
    border: none;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    display: none;
    z-index: 9998;
  `;
  document.body.appendChild(iframe);

  const button = document.createElement("button");
  button.id = "chat-toggle";
  button.innerText = "💬";
  button.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: #df0b0b;
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 24px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    z-index: 9999;
  `;
  document.body.appendChild(button);

  button.addEventListener("click", () => {
    iframe.style.display = iframe.style.display === "none" || iframe.style.display === "" ? "block" : "none";
  });
})();
