import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getAccessToken, onAuthChange } from "./api";
import "./admin.css";

type Tab = "overview" | "users" | "skills" | "events";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function UserCreateForm({ onDone }: { onDone: () => void }) {
  const [login, setLogin] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"member" | "admin">("member");
  const mutation = useMutation({
    mutationFn: () => api.createUser({ login, display_name: displayName.trim() || null, temporary_password: password, role }),
    onSuccess: onDone,
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <form className="admin-form" onSubmit={submit}>
      <div className="admin-form-grid">
        <label>Логин<input value={login} onChange={(e) => setLogin(e.target.value)} required minLength={3} /></label>
        <label>Имя <small>(необязательно)</small><input value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Если пусто, будет использоваться логин" /></label>
        <label>Временный пароль<input value={password} onChange={(e) => setPassword(e.target.value)} required minLength={10} /></label>
        <label>Роль<select value={role} onChange={(e) => setRole(e.target.value as "member" | "admin")}><option value="member">Участник</option><option value="admin">Администратор</option></select></label>
      </div>
      {mutation.isError && <div className="admin-error">{mutation.error.message}</div>}
      <button className="admin-primary" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Создаём…" : "Создать пользователя"}</button>
    </form>
  );
}

export default function AdminPanel() {
  const queryClient = useQueryClient();
  const [authenticated, setAuthenticated] = useState(Boolean(getAccessToken()));
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [sourceSkillId, setSourceSkillId] = useState("");
  const [targetSkillId, setTargetSkillId] = useState("");

  useEffect(() => onAuthChange(() => setAuthenticated(Boolean(getAccessToken()))), []);

  const me = useQuery({ queryKey: ["me-admin"], queryFn: api.me, enabled: authenticated });
  const enabled = authenticated && me.data?.role === "admin" && open;
  const summary = useQuery({ queryKey: ["admin-summary"], queryFn: api.adminSummary, enabled });
  const users = useQuery({ queryKey: ["admin-users"], queryFn: api.users, enabled });
  const skills = useQuery({ queryKey: ["admin-skills"], queryFn: api.skills, enabled });
  const events = useQuery({ queryKey: ["admin-events"], queryFn: api.adminEvents, enabled });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
      queryClient.invalidateQueries({ queryKey: ["admin-skills"] }),
      queryClient.invalidateQueries({ queryKey: ["admin-events"] }),
      queryClient.invalidateQueries({ queryKey: ["skills"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["events"] }),
    ]);
  };

  const userMutation = useMutation({
    mutationFn: ({ id, isActive, role }: { id: number; isActive?: boolean; role?: "admin" | "member" }) =>
      api.updateAdminUser(id, { is_active: isActive, role }),
    onSuccess: refresh,
  });
  const mergeMutation = useMutation({
    mutationFn: () => api.mergeSkill(Number(sourceSkillId), Number(targetSkillId)),
    onSuccess: async () => {
      setSourceSkillId("");
      setTargetSkillId("");
      await refresh();
    },
  });
  const cancelMutation = useMutation({ mutationFn: api.adminCancelEvent, onSuccess: refresh });

  const sortedSkills = useMemo(() => [...(skills.data ?? [])].sort((a, b) => a.name.localeCompare(b.name, "ru")), [skills.data]);

  if (!authenticated || !me.data || me.data.role !== "admin") return null;

  return (
    <>
      <button className="admin-launcher" type="button" onClick={() => setOpen(true)}>
        <span>21</span><strong>Админка</strong>
      </button>
      {open && (
        <div className="admin-overlay">
          <div className="admin-shell">
            <aside className="admin-sidebar">
              <div className="admin-brand"><span>21</span><div><strong>SkillPeer21</strong><small>Admin workspace</small></div></div>
              <nav>
                <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>Обзор</button>
                <button className={tab === "users" ? "active" : ""} onClick={() => setTab("users")}>Пользователи</button>
                <button className={tab === "skills" ? "active" : ""} onClick={() => setTab("skills")}>Навыки</button>
                <button className={tab === "events" ? "active" : ""} onClick={() => setTab("events")}>Встречи</button>
              </nav>
              <div className="admin-side-footer"><span>{me.data.display_name}</span><button onClick={() => setOpen(false)}>Вернуться в сервис</button></div>
            </aside>

            <main className="admin-main">
              <header className="admin-header"><div><span>Управление сообществом</span><h1>{tab === "overview" ? "Обзор" : tab === "users" ? "Пользователи" : tab === "skills" ? "Навыки" : "Встречи"}</h1></div><button className="admin-close" onClick={() => setOpen(false)}>×</button></header>

              {tab === "overview" && (
                <section>
                  <div className="admin-metrics">
                    <article><span>Участники</span><strong>{summary.data?.users_total ?? "—"}</strong><small>{summary.data?.users_active ?? 0} активных</small></article>
                    <article><span>Навыки</span><strong>{summary.data?.skills_total ?? "—"}</strong><small>в общем каталоге</small></article>
                    <article><span>Встречи</span><strong>{summary.data?.events_total ?? "—"}</strong><small>{summary.data?.events_completed ?? 0} завершено</small></article>
                    <article><span>Kudos</span><strong>{summary.data?.kudos_total ?? "—"}</strong><small>благодарностей</small></article>
                  </div>
                  <div className="admin-overview-grid">
                    <section className="admin-card"><span className="admin-eyebrow">Воронка встреч</span><h2>От идеи до проведённой встречи</h2><div className="status-bars"><div><span>Согласование</span><strong>{summary.data?.events_scheduling ?? 0}</strong></div><div><span>Подтверждены</span><strong>{summary.data?.events_confirmed ?? 0}</strong></div><div><span>Завершены</span><strong>{summary.data?.events_completed ?? 0}</strong></div></div></section>
                    <section className="admin-card admin-note"><span className="admin-eyebrow">Принцип</span><h2>Минимум ручного контроля</h2><p>Пользователи сами создают навыки и встречи. Администратор вмешивается в исключения: дубли, неактивные аккаунты и проблемные встречи.</p></section>
                  </div>
                </section>
              )}

              {tab === "users" && (
                <section>
                  <div className="admin-section-head"><div><span className="admin-eyebrow">Доступ только по приглашению</span><h2>Аккаунты School 21</h2></div><button className="admin-primary compact" onClick={() => setShowCreateUser((v) => !v)}>{showCreateUser ? "Закрыть форму" : "+ Пользователь"}</button></div>
                  {showCreateUser && <div className="admin-card admin-create-card"><UserCreateForm onDone={async () => { setShowCreateUser(false); await refresh(); }} /></div>}
                  <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Участник</th><th>Логин</th><th>Роль</th><th>Статус</th><th></th></tr></thead><tbody>{users.data?.map((user) => <tr key={user.id}><td><strong>{user.display_name}</strong></td><td>@{user.login}</td><td><select value={user.role} disabled={userMutation.isPending} onChange={(e) => userMutation.mutate({ id: user.id, role: e.target.value as "admin" | "member" })}><option value="member">Участник</option><option value="admin">Админ</option></select></td><td><span className={`admin-state ${user.is_active ? "active" : "inactive"}`}>{user.is_active ? "Активен" : "Отключён"}</span></td><td><button className="admin-text-button" disabled={user.id === me.data.id || userMutation.isPending} onClick={() => userMutation.mutate({ id: user.id, isActive: !user.is_active })}>{user.is_active ? "Отключить" : "Включить"}</button></td></tr>)}</tbody></table></div>
                  {userMutation.isError && <div className="admin-error">{userMutation.error.message}</div>}
                </section>
              )}

              {tab === "skills" && (
                <section>
                  <div className="admin-section-head"><div><span className="admin-eyebrow">Каталог сообщества</span><h2>{sortedSkills.length} навыков</h2></div></div>
                  <div className="admin-card merge-card"><div><span className="admin-eyebrow">Склейка дублей</span><h3>Перенести все ссылки и удалить дубль</h3><p>Source будет удалён. Пользовательские навыки и встречи будут переведены на target.</p></div><div className="merge-controls"><label>Удалить<select value={sourceSkillId} onChange={(e) => setSourceSkillId(e.target.value)}><option value="">Source skill</option>{sortedSkills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></label><span>→</span><label>Оставить<select value={targetSkillId} onChange={(e) => setTargetSkillId(e.target.value)}><option value="">Target skill</option>{sortedSkills.filter((skill) => String(skill.id) !== sourceSkillId).map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></label><button className="admin-danger" disabled={!sourceSkillId || !targetSkillId || mergeMutation.isPending} onClick={() => mergeMutation.mutate()}>Склеить</button></div>{mergeMutation.isError && <div className="admin-error">{mergeMutation.error.message}</div>}</div>
                  <div className="skill-admin-grid">{sortedSkills.map((skill) => <article key={skill.id}><span>#{skill.id}</span><strong>{skill.name}</strong><small>{skill.created_by_user_id ? `добавлен участником #${skill.created_by_user_id}` : "системный"}</small></article>)}</div>
                </section>
              )}

              {tab === "events" && (
                <section>
                  <div className="admin-section-head"><div><span className="admin-eyebrow">Контроль встреч</span><h2>Все события</h2></div></div>
                  <div className="event-admin-list">{events.data?.map((event) => <article className="admin-card event-admin-row" key={event.id}><div className="event-admin-main"><span className={`admin-state ${event.status}`}>{event.status}</span><h3>{event.title}</h3><p>{event.skill_name} · преподаватель {event.teacher_name} · создал {event.creator_name}</p></div><div className="event-admin-meta"><strong>{event.participants_count}</strong><span>участников</span><small>{formatDate(event.created_at)}</small></div>{event.status !== "completed" && event.status !== "cancelled" && <button className="admin-danger ghost" disabled={cancelMutation.isPending} onClick={() => cancelMutation.mutate(event.id)}>Отменить</button>}</article>)}</div>
                  {cancelMutation.isError && <div className="admin-error">{cancelMutation.error.message}</div>}
                </section>
              )}
            </main>
          </div>
        </div>
      )}
    </>
  );
}