// ======= UTILITIES ==================================================
const escapeHtml = (val) => {
	if (val === null || val === undefined) return "";
	return String(val);
};

const truncate = (val, max = 50) => {
	const s = String(val ?? "");
	return s.length > max ? `${s.slice(0, max)}…` : s;
};

const updateProgressBar = (barEl, percentage) => {
	const p = Math.max(0, Math.min(100, percentage | 0));
	barEl.style.width = `${p}%`;
	barEl.textContent = `${p}%`;
};

// ======= TABLE RENDERING ============================================
const renderTable = (data, progress, progressBar) => {
	return new Promise((resolve) => {
		const gettext = window.gettext || ((message) => message);
		const table = document.querySelector(".csv-table");
		if (!table) return resolve([]);

		table.innerHTML = "";

		// show progress
		progress?.classList?.add("active");
		updateProgressBar(progressBar, 0);

		if (!Array.isArray(data) || data.length === 0) {
			const empty = document.createElement("caption");
			empty.textContent = gettext("No data to import");
			table.appendChild(empty);
			return resolve([]);
		}

		// thead
		const thead = document.createElement("thead");
		const headerRow = document.createElement("tr");
		const headers = Object.keys(data[0] ?? {});
		headers.forEach((key) => {
			const th = document.createElement("th");
			th.textContent = key;
			headerRow.appendChild(th);
		});
		const statusTh = document.createElement("th");
		statusTh.textContent = gettext("Status");
		headerRow.insertBefore(statusTh, headerRow.firstChild);
		thead.appendChild(headerRow);
		table.appendChild(thead);

		// tbody
		const tbody = document.createElement("tbody");
		let index = 0;

		for (const row of data) {
			index += 1;
			const tr = document.createElement("tr");
			tr.id = `row-${index}`;

			headers.forEach((key) => {
				const raw = row[key];
				const td = document.createElement("td");
				const display = escapeHtml(truncate(raw, 50));
				td.textContent = display;
				tr.appendChild(td);
			});

			const statusTd = document.createElement("td");
			statusTd.classList.add("status-message");
			tr.insertBefore(statusTd, tr.firstChild);

			tbody.appendChild(tr);
		}

		table.appendChild(tbody);
		resolve(data);
	});
};

window.MadlobaAdminCsvImport = Object.freeze({
	renderTable,
});
