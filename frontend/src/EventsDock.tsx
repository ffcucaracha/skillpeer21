import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getAccessToken, onAuthChange, type CommunityEvent } from "./api";
import "./events.css";

type EventsMode = "active" | "history" | "create";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusLabel(status: CommunityEvent["status"]): string {
  if (status === "confirmed") return "Время выбрано";
  if (status === "completed") return "Завершена";
  if (status === "cancelled") return "Отменена";
  return "Ищем время";
}

function EventCard({ event, currentUserId }: { event: CommunityEvent; currentUserId: number }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const participant = event.participants.some((item) => item.user_id === currentUserId);
  const isCreator = event.creator_id === currentUserId;

  const refresh = async () => {
    setError(null);
    await queryClient.invalidateQueries({ queryKey: ["events"] });
  };

  const join = useMutation({ mutationFn: () => api.joinEvent(event.id), onSuccess: refresh, onError: (e: Error) => setError(e.message) });
  const vote = useMutation({ mutationFn: (optionId: number) => api.voteEventTime(event.id, optionId), onSuccess: refresh, onError: (e: Error) => setError(e.message) });
  const confirm = useMutation({ mutationFn: (optionId: number) => api.confirmEventTime(event.id, optionId), onSuccess: refresh, onError: (e: Error) => setError(e.message) });
  const complete = useMutation({ mutationFn: () => api.completeEvent(event.id), onSuccess: refresh, onError: (e: Error) => setError(e.message) });
  const kudos = useMutation({ mutationFn: (recipientId: number) => api.giveKudos(event.id, recipientId), onSuccess: refresh, onError: (e: Error) => setError(e.message) });

  const confirmedOption = event.time_options.find((option) => option.id === event.confirmed_time_option_id);

  return (
    <article className={`event-card ${event.status}`}>
      <div className="event-card-head">
        <div><span className="event-skill">{event.skill_name}</span><h3>{event.title}</h3></div>
        <span className={`event-status ${event.status}`}>{statusLabel(event.status)}</span>
      </div>
      {event.description && <p className="event-description">{event.description}</p>}
      <div className="event-people">
        <span>{event.participants.find((item) => item.role === "teacher")?.display_name} · преподаватель</span>
        <span>{event.participants.filter((item) => item.role === "learner").length} участников</span>
      </div>

      {event.status === "completed" ? (
        <div className="kudos-section">
          <div className="kudos-heading"><strong>Скажи спасибо пирам</strong><span>Kudos — без рейтингов и оценок</span></div>
          <div className="kudos-list">
            {event.participants.map((person) => (
              <div className="kudos-person" key={person.user_id}>
                <span className="kudos-avatar">{person.display_name.slice(0, 2).toUpperCase()}</span>
                <span className="kudos-name"><strong>{person.display_name}</strong><small>{person.role === "teacher" ? "преподаватель" : "участник"} · ♥ {person.kudos_received}</small></span>
                {person.user_id !== currentUserId && participant && (
                  <button type="button" className={person.kudos_given_by_me ? "kudos-button given" : "kudos-button"} disabled={person.kudos_given_by_me || kudos.isPending} onClick={() => kudos.mutate(person.user_id)}>
                    {person.kudos_given_by_me ? "Спасибо ✓" : "Дать kudos"}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : event.status === "cancelled" ? (
        <div className="cancelled-note">Эта встреча отменена.</div>
      ) : event.status === "confirmed" && confirmedOption ? (
        <>
          <div className="confirmed-slot"><strong>{formatDate(confirmedOption.starts_at)}</strong><span>встреча подтверждена</span></div>
          {isCreator && <button className="complete-event" type="button" disabled={complete.isPending} onClick={() => complete.mutate()}>{complete.isPending ? "Завершаем…" : "Отметить встречу завершённой"}</button>}
        </>
      ) : (
        <div className="slot-list">
          {event.time_options.map((option) => (
            <div className={`slot-row ${option.voted_by_me ? "selected" : ""}`} key={option.id}>
              <button type="button" disabled={!participant || vote.isPending} onClick={() => vote.mutate(option.id)}>
                <span className="slot-check">{option.voted_by_me ? "✓" : ""}</span>
                <span><strong>{formatDate(option.starts_at)}</strong><small>{option.votes_count} голосов{option.teacher_voted ? " · преподаватель может" : ""}</small></span>
              </button>
              {isCreator && option.teacher_voted && <button className="confirm-slot" type="button" disabled={confirm.isPending} onClick={() => confirm.mutate(option.id)}>Выбрать</button>}
            </div>
          ))}
        </div>
      )}

      {!participant && event.status === "scheduling" && <button className="event-secondary" type="button" disabled={join.isPending} onClick={() => join.mutate()}>Присоединиться и голосовать</button>}
      {error && <div className="event-error">{error}</div>}
    </article>
  );
}

function CreateEvent({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const [matchIndex, setMatchIndex] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [firstTime, setFirstTime] = useState("");
  const [secondTime, setSecondTime] = useState("");

  const matches = dashboard.data?.matches ?? [];
  const selectedMatch = matchIndex === "" ? null : matches[Number(matchIndex)];

  const mutation = useMutation({
    mutationFn: () => api.createEvent({
      skill_id: selectedMatch!.skill_id,
      teacher_id: Number(teacherId),
      title,
      description: description || undefined,
      time_options: [new Date(firstTime).toISOString(), new Date(secondTime).toISOString()],
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["events"] });
      onDone();
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedMatch || !teacherId || !firstTime || !secondTime) return;
    mutation.mutate();
  }

  return (
    <form className="event-create" onSubmit={submit}>
      <div className="event-form-title"><span>Новая встреча</span><strong>Собери пиров вокруг навыка</strong></div>
      {matches.length === 0 ? <div className="event-empty-note">Сначала добавь навык, которому хочешь научиться, и дождись совпадения с преподавателем.</div> : (
        <>
          <label>Навык<select value={matchIndex} onChange={(e) => { setMatchIndex(e.target.value); setTeacherId(""); }} required><option value="">Выбери навык</option>{matches.map((match, index) => <option key={match.skill_id} value={index}>{match.skill_name}</option>)}</select></label>
          <label>Преподаватель<select value={teacherId} onChange={(e) => setTeacherId(e.target.value)} required disabled={!selectedMatch}><option value="">Выбери пира</option>{selectedMatch?.teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.display_name}</option>)}</select></label>
          <label>Название встречи<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Например, Гитара с нуля" minLength={3} required /></label>
          <label>Что хотите разобрать<textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Коротко опиши цель первой встречи" rows={3} /></label>
          <div className="time-grid"><label>Вариант 1<input type="datetime-local" value={firstTime} onChange={(e) => setFirstTime(e.target.value)} required /></label><label>Вариант 2<input type="datetime-local" value={secondTime} onChange={(e) => setSecondTime(e.target.value)} required /></label></div>
          {mutation.isError && <div className="event-error">{mutation.error.message}</div>}
          <button className="event-primary" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Создаём…" : "Создать встречу"}</button>
        </>
      )}
    </form>
  );
}

export default function EventsDock() {
  const [authenticated, setAuthenticated] = useState(Boolean(getAccessToken()));
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<EventsMode>("active");

  useEffect(() => onAuthChange(() => setAuthenticated(Boolean(getAccessToken()))), []);
  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent<EventsMode>).detail;
      setMode(detail || "active");
      setOpen(true);
    };
    window.addEventListener("skillpeer21-open-events", handler);
    return () => window.removeEventListener("skillpeer21-open-events", handler);
  }, []);

  const me = useQuery({ queryKey: ["me-events"], queryFn: api.me, enabled: authenticated });
  const events = useQuery({ queryKey: ["events"], queryFn: api.events, enabled: authenticated });
  const allEvents = useMemo(() => events.data ?? [], [events.data]);
  const visibleEvents = mode === "history"
    ? allEvents.filter((event) => event.status === "completed" || event.status === "cancelled")
    : allEvents.filter((event) => event.status === "scheduling" || event.status === "confirmed");

  if (!authenticated || !me.data || !open) return null;

  return (
    <div className="events-drawer-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) setOpen(false); }}>
      <section className="events-panel events-drawer" aria-label="Встречи SkillPeer21">
        <header className="events-drawer-header">
          <div><span>SkillPeer21</span><h2>{mode === "history" ? "История встреч" : mode === "create" ? "Новая встреча" : "Встречи"}</h2></div>
          <button className="drawer-close" type="button" onClick={() => setOpen(false)} aria-label="Закрыть">×</button>
        </header>
        <div className="events-tabs">
          <button type="button" className={mode === "active" ? "active" : ""} onClick={() => setMode("active")}>Встречи</button>
          <button type="button" className={mode === "history" ? "active" : ""} onClick={() => setMode("history")}>История</button>
          <button type="button" className={mode === "create" ? "active create" : "create"} onClick={() => setMode("create")}>+ Создать</button>
        </div>
        {mode === "create" ? <CreateEvent onDone={() => setMode("active")} /> : (
          <div className="events-list">
            {events.isLoading && <div className="event-empty-note">Загружаем встречи…</div>}
            {events.isError && <div className="event-error">Не удалось загрузить встречи.</div>}
            {!events.isLoading && visibleEvents.length === 0 && <div className="events-empty"><div>21</div><strong>{mode === "history" ? "История пока пуста" : "Пока тихо"}</strong><p>{mode === "history" ? "Завершённые и отменённые встречи появятся здесь." : "Создай первую встречу вокруг навыка, для которого уже нашёлся преподаватель."}</p>{mode === "active" && <button type="button" onClick={() => setMode("create")}>Создать встречу</button>}</div>}
            {visibleEvents.map((event) => <EventCard key={event.id} event={event} currentUserId={me.data.id} />)}
          </div>
        )}
      </section>
    </div>
  );
}
