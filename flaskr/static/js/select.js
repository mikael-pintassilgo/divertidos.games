fetchElementsForSelection = function(page) {
    serchString = document.getElementById('search_term').value;
    
    finalSelectURL = selectURL;
    console.log('1 finalSelectURL = ', finalSelectURL);
    finalSelectURL = finalSelectURL + '&page=' + page;
    console.log('2 finalSelectURL = ', finalSelectURL);
    /*
    if (serchString) {
        finalSelectURL += '&search=' + serchString;
    }
    console.log('3 finalSelectURL = ', finalSelectURL);
    */
    fetch(selectURL + '?page=' + page + '&search=' + serchString)
    .then(response => response.json())
    .then(data => {
        const elementsList = document.getElementById('elementsList');
        elementsList.innerHTML = '';
        data.elements.forEach(element => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'list-group-item list-group-item-action text-start p-3';
            button.innerHTML = `<h6 class="mb-1">${element.title}</h6><p class="mb-1 small text-muted">${element.body.substring(0, 100)}</p>`;
            button.onclick = () => selectElement(element.id, element.title);
            elementsList.appendChild(button);
        });
    });
};

document.getElementById('previous_page_btn').addEventListener('click', function() {
    currentPage -= 1;
    if (currentPage < 1) {
        currentPage = 1;
    };
    console.log('currentPage = ', currentPage);
    fetchElementsForSelection(currentPage);
});

document.getElementById('next_page_btn').addEventListener('click', function() {
currentPage += 1;
console.log('currentPage = ', currentPage);
    fetchElementsForSelection(currentPage);
});

document.getElementById('selectElementBtn').addEventListener('click', function() {
    fetchElementsForSelection(1);
});

document.getElementById('searchElementBtn').addEventListener('click', function() {
    fetchElementsForSelection(1);
});

document.getElementById('clearSearchElementBtn').addEventListener('click', function() {
    document.getElementById('search_term').value = '';
    fetchElementsForSelection(1);
});

function selectElement(elementId, elementTitle) {
    document.getElementById('element_id').value = elementId;
    elementLink = document.getElementById('viewElementLink');
    elementLink.href = '/' + elementId + '/view';
    elementLink.textContent = '' + elementTitle;
    bootstrap.Offcanvas.getInstance(document.getElementById('elementPanel')).hide();
}