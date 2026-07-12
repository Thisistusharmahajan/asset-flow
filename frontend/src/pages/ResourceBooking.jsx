import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import Sidebar from "../components/Sidebar";
import "./ResourceBooking.css";

const HOURS = [9, 10, 11, 12, 13]; // 9:00 - 1:00, matching the mockup's visible range

function toDateInputValue(d) {
  return d.toISOString().slice(0, 10);
}

function formatHourLabel(h) {
  const hour12 = h > 12 ? h - 12 : h;
  return `${hour12}:00`;
}

function timeToMinutes(iso) {
  const d = new Date(iso);
  return d.getHours() * 60 + d.getMinutes();
}

export default function ResourceBooking() {
  const [resources, setResources] = useState([]);
  const [resourceId, setResourceId] = useState("");
  const [date, setDate] = useState(toDateInputValue(new Date()));

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showBookModal, setShowBookModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [conflictNotice, setConflictNotice] = useState(null);

  useEffect(() => {
    api
      .resources()
      .then((res) => {
        setResources(res);
        if (res.length) setResourceId(res[0].id);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const loadBookings = useCallback(() => {
    if (!resourceId) return;
    setError("");
    api
      .bookings({ asset_id: resourceId, date })
      .then(setBookings)
      .catch((err) => setError(err.message));
  }, [resourceId, date]);

  useEffect(() => {
    loadBookings();
  }, [loadBookings]);

  const selectedResource = resources.find((r) => r.id === resourceId);

  async function handleBook(form) {
    setSubmitting(true);
    setError("");
    setConflictNotice(null);
    try {
      const start_time = `${date}T${form.start}:00`;
      const end_time = `${date}T${form.end}:00`;
      await api.createBooking({
        asset_id: resourceId,
        start_time,
        end_time,
      });
      setShowBookModal(false);
      loadBookings();
    } catch (err) {
      setConflictNotice(`Requested ${form.start} to ${form.end} - conflict - slot is unavailble`);
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="shell">
      <Sidebar active="Resource Booking" />
      <main className="content">
        <header className="content-header">
          <h1>Resource Booking</h1>
        </header>

        {error && <div className="banner banner-error">{error}</div>}

        <div className="booking-panel">
          <label className="booking-field">
            <span>Resource</span>
            <div className="booking-resource-row">
              <select value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
                {resources.length === 0 && <option value="">No bookable resources</option>}
                {resources.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                    {r.location ? ` - ${r.location}` : ""}
                  </option>
                ))}
              </select>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="booking-date"
              />
            </div>
          </label>

          {loading ? (
            <p className="empty-state">Loading…</p>
          ) : (
            <div className="timeline">
              {HOURS.map((h) => {
                const slotStart = h * 60;
                const slotEnd = slotStart + 60;
                const booking = bookings.find((b) => {
                  const s = timeToMinutes(b.start_time);
                  const e = timeToMinutes(b.end_time);
                  return s < slotEnd && e > slotStart;
                });

                return (
                  <div className="timeline-row" key={h}>
                    <span className="timeline-hour">{formatHourLabel(h)}</span>
                    <div className="timeline-track">
                      {booking && (
                        <div className={"timeline-slot slot-" + booking.status.toLowerCase()}>
                          Booked - {booking.booked_by_name || "Reserved"} -{" "}
                          {new Date(booking.start_time).toLocaleTimeString([], {
                            hour: "numeric",
                            minute: "2-digit",
                          })}{" "}
                          to{" "}
                          {new Date(booking.end_time).toLocaleTimeString([], {
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {conflictNotice && (
                <div className="timeline-conflict">{conflictNotice}</div>
              )}
            </div>
          )}

          <button
            className="book-slot-btn"
            onClick={() => {
              setConflictNotice(null);
              setShowBookModal(true);
            }}
            disabled={!resourceId}
          >
            Book a slot
          </button>
        </div>
      </main>

      {showBookModal && (
        <BookSlotModal
          resourceName={selectedResource?.name}
          submitting={submitting}
          onCancel={() => setShowBookModal(false)}
          onSave={handleBook}
        />
      )}
    </div>
  );
}

function BookSlotModal({ resourceName, submitting, onCancel, onSave }) {
  const [form, setForm] = useState({ start: "09:00", end: "10:00" });

  function update(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>Book a slot{resourceName ? ` — ${resourceName}` : ""}</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSave(form);
          }}
        >
          <div className="modal-row">
            <label className="modal-field">
              <span>Start time</span>
              <input type="time" value={form.start} onChange={update("start")} required />
            </label>
            <label className="modal-field">
              <span>End time</span>
              <input type="time" value={form.end} onChange={update("end")} required />
            </label>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Booking…" : "Book slot"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}