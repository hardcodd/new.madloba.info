document.addEventListener("DOMContentLoaded", () => {
	const form = document.querySelector("#import-comments-form");
	if (!form) return;
	const gettext = window.gettext || ((message) => message);

	const csvImport = window.MadlobaAdminCsvImport;
	if (!csvImport) {
		console.error(gettext("CSV import utilities are unavailable."));
		return;
	}

	const csrf = form.querySelector("input[name='csrfmiddlewaretoken']");
	const progress = document.querySelector("#import-progress");
	const progressBar = progress?.querySelector(".bar");
	const requiredFields = ["id", "text", "user", "date"];
	const batchSize = 100;

	if (!csrf || !progressBar) {
		console.error(gettext("Comment import form controls are unavailable."));
		return;
	}
	if (!window.Papa) {
		console.error(gettext("CSV parser is unavailable."));
		return;
	}

	const setProgress = (processed, total) => {
		const percentage = total ? Math.round((processed / total) * 100) : 100;
		progress.classList.add("active");
		progressBar.style.width = `${percentage}%`;
		progressBar.textContent = `${percentage}%`;
	};

	const setRowResult = (index, result) => {
		const row = document.getElementById(`row-${index + 1}`);
		const status = row?.querySelector(".status-message");
		if (!row || !status) return;

		row.classList.remove("success", "warning", "error");
		if (result.success) {
			row.classList.add("success");
			status.textContent = gettext("Imported!");
			return;
		}

		row.classList.add(result.code === "already_exists" ? "warning" : "error");
		status.textContent = result.message;
	};

	const postBatch = async (rows) => {
		const response = await fetch(form.action, {
			method: "POST",
			credentials: "same-origin",
			headers: {
				"Content-Type": "application/json",
				"X-CSRFToken": csrf.value,
			},
			body: JSON.stringify(rows),
		});

		let data;
		try {
			data = await response.json();
		} catch (_) {
			throw new Error(`HTTP ${response.status}`);
		}

		if (!response.ok || !data.success || !Array.isArray(data.results)) {
			throw new Error(data.message || `HTTP ${response.status}`);
		}
		if (data.results.length !== rows.length) {
			throw new Error(gettext("The server returned an incomplete import result."));
		}
		return data.results;
	};

	const importRows = async (rows) => {
		let processed = 0;
		let successful = 0;
		let warnings = 0;
		let errors = 0;
		setProgress(0, rows.length);

		for (let offset = 0; offset < rows.length; offset += batchSize) {
			const batch = rows.slice(offset, offset + batchSize);
			let results;
			try {
				results = await postBatch(batch);
			} catch (error) {
				results = batch.map(() => ({
					success: false,
					code: "request_failed",
					message: error.message || gettext("Import request failed."),
				}));
			}

			results.forEach((result, index) => {
				setRowResult(offset + index, result);
				if (result.success) successful += 1;
				else if (result.code === "already_exists") warnings += 1;
				else errors += 1;
			});
			processed += batch.length;
			setProgress(processed, rows.length);
		}

		const tableBody = document.querySelector(".csv-table tbody");
		tableBody
			?.querySelectorAll("tr.warning, tr.error")
			.forEach((row) => tableBody.appendChild(row));
		alert(
			`${gettext("Import completed")}: ${processed}/${rows.length}. ` +
				`${gettext("Successful")}: ${successful}. ` +
				`${gettext("Warnings")}: ${warnings}. ` +
				`${gettext("Errors")}: ${errors}.`,
		);
	};

	form.addEventListener("submit", (event) => {
		event.preventDefault();

		const file = form.file?.files?.[0];
		if (!file) return;

		window.Papa.parse(file, {
			header: true,
			skipEmptyLines: "greedy",
			transformHeader: (header) => header.replace(/^\uFEFF/, "").trim(),
			encoding: "utf-8",
			complete: async (result) => {
				const fields = result.meta?.fields || [];
				const missingFields = requiredFields.filter(
					(field) => !fields.includes(field),
				);
				if (missingFields.length) {
					alert(
						`${gettext("Missing required CSV fields")}: ${missingFields.join(", ")}`,
					);
					return;
				}

				const rows = (result.data || []).map((row) => ({
					id: row.id,
					text: row.text,
					user: row.user,
					date: row.date,
				}));

				await csvImport.renderTable(rows, progress, progressBar);
				const controls = form.querySelectorAll("input, button");
				controls.forEach((control) => {
					control.disabled = true;
				});
				try {
					await importRows(rows);
				} finally {
					controls.forEach((control) => {
						control.disabled = false;
					});
				}
			},
			error: (error) => alert(`${gettext("Parsing error")}: ${error.message}`),
		});
	});
});
