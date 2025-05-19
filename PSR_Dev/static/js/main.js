const title = document.querySelector('.text-container h2');

title.innerHTML = title.textContent.split(' ').map(word =>
    `<strong>${word.chartAt(0)}</strong>${word.slice(1)}`   
).join(' ');