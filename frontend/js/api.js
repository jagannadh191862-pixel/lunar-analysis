async getHistory(limit = 20) {
  try {
    const res = await fetch(
      `${API_BASE}/analysis/history?limit=${limit}`
    );

    const text = await res.text();

    let data;

    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }

    console.log("History API status:", res.status);
    console.log("History API response:", data);

    if (!res.ok) {
      throw new Error(
        data.message ||
        data.error ||
        `History request failed with status ${res.status}`
      );
    }

    return data;

  } catch (error) {
    console.error("getHistory() failed:", error);
    throw error;
  }
}
