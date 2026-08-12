import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, clearTokens, getAccessToken, saveTokens, type Dashboard, type Skill, type User, type UserSkill } from "./api";

type SkillIntent = "teach" | "learn";
type CommunityView = "members" | "skills" | "teachers";
type IconName = "spark" | "people" | "book" | "teach" | "learn" | "plus" | "logout" | "arrow" | "calendar" | "history" | "edit";

function Icon({ name }: { name: IconName }) {
  const common = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8 };
  const paths: Record<IconName, React.ReactNode> = {
    spark: <path d="M12 3l1.5 4.3L18 9l-4.5 1.7L12 15l-1.5-4.3L6 9l4.5-1.7L12 3Zm6.5 11 .8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z" />,
    people: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" /></>,
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" /></>,
    teach: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v15H6.5A2.5 2.5 0 0 0 4 19.5V4.5A2.5 2.5 0 0 1 6.5 2Z" /><path d="M9 7h7M9 11h4" /></>,
    learn: <><path d="m3 10 9-5 9 5-9 5-9-5Z" /><path d="M7 12.5v4.2c2.8 2 7.2 2 10 0v-4.2" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5M21 12H9" /></>,
    arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></>,
    history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l3 2" /></>,
    edit: <><path d="M12 20h9" /><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z" /></>,
  };
  return <svg {...common} aria-hidden="true">{paths[name]}</svg>;
}

function openEvents(mode: "active" | "history" | "create") {
  window.dispatchEvent(new CustomEvent("skillpeer21-open-events", { detail: mode }));
}

function LoginScreen({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({ mutationFn: () => api.login(login, password), onSuccess: (tokens) => { saveTokens(tokens); onLoggedIn(); } });
  function submit(event: FormEvent) { event.preventDefault(); mutation.mutate(); }
  return <main className="login-page brand-login">
    <section className="login-brand brand-login-hero">
      <div className="login-brand-lockup"><div className="brand-mark">21</div><strong>School 21</strong></div>
      <span>SkillPeer21 community</span>
      <h1>Навыки становятся сильнее, когда ими <em>делятся.</em></h1>
      <p>SkillPeer21 соединяет тех, кто хочет научиться, с теми, кто готов передать свой опыт.</p>
      <img className="login-cat" src="/space-cat.svg" alt="Кот-астронавт SkillPeer21" />
      <div className="brand-points"><span><Icon name="spark" /> Находи совпадения по интересам</span><span><Icon name="people" /> Учись у равных и учи сам</span></div>
    </section>
    <section className="login-panel brand-login-panel"><form className="login-card brand-login-card" onSubmit={submit}>
      <div className="login-orbit-mark"><Icon name="spark" /></div>
      <div><span className="kicker">Добро пожаловать в</span><h2>SkillPeer<span>21</span></h2><p>Используй логин и временный пароль, выданные администратором.</p></div>
      <label>Логин<input value={login} onChange={(event) => setLogin(event.target.value)} autoComplete="username" placeholder="Введите логин" required /></label>
      <label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" placeholder="Введите пароль" required /></label>
      {mutation.isError && <div className="error-message">Не удалось войти. Проверь логин и пароль.</div>}
      <button className="primary-button" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Входим…" : "Войти"}{!mutation.isPending && <Icon name="arrow" />}</button>
    </form></section>
  </main>;
}

function SkillPicker({ skills, initialIntent, onDone }: { skills: Skill[]; initialIntent: SkillIntent; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [selectedSkillId, setSelectedSkillId] = useState<number | null>(null);
  const [intent, setIntent] = useState<SkillIntent>(initialIntent);
  const createMutation = useMutation({ mutationFn: () => api.createSkill(name) });
  const linkMutation = useMutation({ mutationFn: ({ skillId, skillIntent }: { skillId: number; skillIntent: SkillIntent }) => api.addSkillIntent(skillId, skillIntent), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["dashboard"] }), queryClient.invalidateQueries({ queryKey: ["skills"] }), queryClient.invalidateQueries({ queryKey: ["my-skills"] })]); setName(""); setSelectedSkillId(null); onDone(); } });
  async function addNewSkill() { if (!name.trim()) return; try { const skill = await createMutation.mutateAsync(); await linkMutation.mutateAsync({ skillId: skill.id, skillIntent: intent }); } catch {} }
  async function addExistingSkill() { if (!selectedSkillId) return; try { await linkMutation.mutateAsync({ skillId: selectedSkillId, skillIntent: intent }); } catch {} }
  const busy = createMutation.isPending || linkMutation.isPending;
  const error = createMutation.error?.message || linkMutation.error?.message;
  return <div className="skill-editor"><div className="intent-toggle" role="group" aria-label="Тип навыка"><button type="button" className={intent === "teach" ? "active" : ""} onClick={() => setIntent("teach")}><Icon name="teach" /> Могу научить</button><button type="button" className={intent === "learn" ? "active" : ""} onClick={() => setIntent("learn")}><Icon name="learn" /> Хочу научиться</button></div><div className="editor-grid"><label>Выбрать из каталога<select value={selectedSkillId ?? ""} onChange={(event) => setSelectedSkillId(event.target.value ? Number(event.target.value) : null)}><option value="">Выбери навык</option>{skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></label><button className="secondary-button" type="button" onClick={addExistingSkill} disabled={!selectedSkillId || busy}>Добавить</button></div><div className="or-divider"><span>или добавить новый навык</span></div><div className="editor-grid"><label>Новый навык<input placeholder="Например, фотография" value={name} onChange={(event) => setName(event.target.value)} /></label><button className="secondary-button" type="button" onClick={addNewSkill} disabled={!name.trim() || busy}>Создать</button></div>{error && <div className="error-message">{error}</div>}</div>;
}

function ProfileEditor({ user, onDone }: { user: User; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(user.display_name === user.login ? "" : user.display_name);
  const [telegram, setTelegram] = useState(user.telegram_username ?? "");
  const [visibility, setVisibility] = useState<User["telegram_visibility"]>(user.telegram_visibility);
  const mutation = useMutation({
    mutationFn: () => api.updateProfile({ display_name: displayName.trim() || null, telegram_username: telegram.trim() || null, telegram_visibility: visibility }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["me"] }),
        queryClient.invalidateQueries({ queryKey: ["me-admin"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      ]);
      onDone();
    },
  });
  return <section className="panel editor-panel profile-editor"><div className="section-heading"><div><span className="kicker">Мой профиль</span><h2>Имя и контакты</h2></div><button className="text-button" type="button" onClick={onDone}>Закрыть</button></div><div className="profile-form"><label>Имя<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder={`Если пусто — ${user.login}`} /></label><label>Telegram<input value={telegram} onChange={(event) => setTelegram(event.target.value)} placeholder="username или @username" /></label><fieldset><legend>Кому показывать Telegram</legend><label className="visibility-option"><input type="radio" name="visibility" checked={visibility === "everyone"} onChange={() => setVisibility("everyone")} /><span><strong>Всем участникам</strong><small>Контакт будет виден в совпадениях и списках сообщества.</small></span></label><label className="visibility-option"><input type="radio" name="visibility" checked={visibility === "admin_only"} onChange={() => setVisibility("admin_only")} /><span><strong>Только администратору</strong><small>Обычные участники увидят, что контакт скрыт.</small></span></label></fieldset>{mutation.isError && <div className="error-message">{mutation.error.message}</div>}<button className="primary-button compact" type="button" disabled={mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? "Сохраняем…" : "Сохранить"}</button></div></section>;
}

function CommunityModal({ view, dashboard, onClose }: { view: CommunityView; dashboard: Dashboard; onClose: () => void }) {
  const title = view === "members" ? "Участники" : view === "skills" ? "Навыки сообщества" : "Готовы учить";
  return <div className="community-modal-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}><section className="community-modal"><header><div><span className="kicker">SkillPeer21</span><h2>{title}</h2></div><button className="community-close" type="button" onClick={onClose}>×</button></header><div className="community-list">
    {view === "members" && dashboard.members.map((member) => <article className="community-person" key={member.id}><div><strong>{member.display_name}</strong><span> {member.telegram_username ? `@${member.telegram_username}` : "Контакт скрыт"}</span></div>{member.telegram_username && <a href={`https://t.me/${member.telegram_username}`} target="_blank" rel="noreferrer">Написать</a>}</article>)}
    {view === "skills" && dashboard.skills.map((skill) => <article className="community-skill" key={skill.skill_id}><strong>{skill.skill_name}</strong><div><span>{skill.teachers_count} могут научить</span><span>{skill.learners_count} хотят научиться</span></div></article>)}
    {view === "teachers" && dashboard.teaching_members.map((teacher) => <article className="community-teacher" key={teacher.id}><div className="community-person-row"><div><strong>{teacher.display_name}</strong><span> {teacher.telegram_username ? `@${teacher.telegram_username}` : "Контакт скрыт"}</span></div>{teacher.telegram_username && <a href={`https://t.me/${teacher.telegram_username}`} target="_blank" rel="noreferrer">Написать</a>}</div><div className="chip-list">{teacher.skills.map((skill) => <span className="chip teach" key={skill}>{skill}</span>)}</div></article>)}
  </div></section></div>;
}

function SkillChip({ skill, onRemove, removing }: { skill: UserSkill; onRemove: (skill: UserSkill) => void; removing: boolean }) {
  return <span className={`chip ${skill.intent}`}><span>{skill.skill_name}</span><button type="button" aria-label={`Удалить ${skill.skill_name}`} title="Убрать из моего профиля" disabled={removing} onClick={() => onRemove(skill)}>×</button></span>;
}

function DashboardPage({ onLogout }: { onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [editorIntent, setEditorIntent] = useState<SkillIntent | null>(null);
  const [communityView, setCommunityView] = useState<CommunityView | null>(null);
  const [profileEditing, setProfileEditing] = useState(false);
  const userQuery = useQuery({ queryKey: ["me"], queryFn: api.me });
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const skillsQuery = useQuery({ queryKey: ["skills"], queryFn: api.skills });
  const mySkillsQuery = useQuery({ queryKey: ["my-skills"], queryFn: api.mySkills });
  const removeSkillMutation = useMutation({ mutationFn: (skill: UserSkill) => api.removeSkillIntent(skill.skill_id, skill.intent), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["my-skills"] }), queryClient.invalidateQueries({ queryKey: ["dashboard"] })]); } });
  const loading = userQuery.isLoading || dashboardQuery.isLoading || skillsQuery.isLoading || mySkillsQuery.isLoading;
  const failed = userQuery.isError || dashboardQuery.isError || skillsQuery.isError || mySkillsQuery.isError;
  const groupedMySkills = useMemo(() => { const result = { teach: [] as UserSkill[], learn: [] as UserSkill[] }; for (const skill of mySkillsQuery.data ?? []) result[skill.intent].push(skill); return result; }, [mySkillsQuery.data]);
  if (loading) return <main className="center-state"><div className="loader" /><p>Собираем твоё комьюнити…</p></main>;
  if (failed || !userQuery.data || !dashboardQuery.data) return <main className="center-state"><h2>Не удалось загрузить дашборд</h2><button className="primary-button" onClick={onLogout}>Войти заново</button></main>;
  const user = userQuery.data;
  const dashboard = dashboardQuery.data;
  const firstName = user.display_name.split(" ")[0];
  return <div className="app-shell"><aside className="sidebar"><div className="logo-row"><div><strong>SkillPeer21</strong><span>peer-to-peer learning</span></div></div><nav><button className="active" type="button"><Icon name="spark" /><span>Главная</span></button><button type="button" onClick={() => openEvents("active")}><Icon name="calendar" /><span>Встречи</span></button><button type="button" onClick={() => openEvents("history")}><Icon name="history" /><span>История встреч</span></button></nav><div className="sidebar-profile"><div><strong>{user.display_name}</strong><span>{user.role === "admin" ? " Администратор" : ""}</span></div><button className="icon-button" type="button" onClick={onLogout} aria-label="Выйти"><Icon name="logout" /></button></div></aside>
    <main className="dashboard"><header className="dashboard-header"><div><span className="kicker">School 21 · обмен опытом</span><h1>Привет, {firstName}.</h1><p>Посмотри, чему сегодня можно научиться у своих пиров.</p></div></header>
      {profileEditing && <ProfileEditor user={user} onDone={() => setProfileEditing(false)} />}
      {editorIntent && <section className="panel editor-panel"><div className="section-heading"><div><span className="kicker">Мой профиль</span><h2>{editorIntent === "teach" ? "Добавить то, чему я могу научить" : "Добавить то, чему я хочу научиться"}</h2></div><button className="text-button" onClick={() => setEditorIntent(null)}>Закрыть</button></div><SkillPicker key={editorIntent} skills={skillsQuery.data ?? []} initialIntent={editorIntent} onDone={() => setEditorIntent(null)} /></section>}
      <section className="metric-grid" aria-label="Статистика сообщества">
        <button className="metric-card accent clickable" type="button" onClick={() => setCommunityView("members")}><span className="metric-icon"><Icon name="people" /></span><div><span>Участников</span><strong>{dashboard.summary.members_count}</strong><small>посмотреть сообщество</small></div></button>
        <button className="metric-card clickable" type="button" onClick={() => setCommunityView("skills")}><span className="metric-icon"><Icon name="book" /></span><div><span>Навыков</span><strong>{dashboard.summary.skills_count}</strong><small>открыть каталог</small></div></button>
        <button className="metric-card clickable" type="button" onClick={() => setCommunityView("teachers")}><span className="metric-icon"><Icon name="teach" /></span><div><span>Готовы учить</span><strong>{dashboard.summary.teaching_members_count}</strong><small>посмотреть участников</small></div></button>
        <article className="metric-card"><span className="metric-icon"><Icon name="spark" /></span><div><span>Совпадений</span><strong>{dashboard.summary.matched_learning_goals_count}</strong><small>навыков с совпадениями</small></div></article>
      </section>
      <section className="content-grid"><div className="main-column"><div className="section-heading"><div><span className="kicker">Твои совпадения</span><h2>Есть у кого научиться</h2></div><span className="count-badge">{dashboard.matches.length}</span></div>{dashboard.matches.length === 0 ? <div className="empty-state panel"><span className="empty-icon"><Icon name="spark" /></span><h3>Пока нет прямых совпадений</h3><p>Добавь навык в «Хочу научиться». Как только кто-то отметит тот же навык как «Могу научить», совпадение появится здесь.</p></div> : <div className="match-list">{dashboard.matches.map((match, index) => <article className={`match-card ${index === 0 ? "featured" : ""}`} key={match.skill_id}><div className="match-top"><div><span className="match-label">Хочу научиться</span><h3>{match.skill_name}</h3></div><span className="teacher-count">{match.teachers.length} {match.teachers.length === 1 ? "пир может научить" : "пира могут научить"}</span></div><div className="teacher-stack">{match.teachers.slice(0, 3).map((teacher) => <div className="teacher-row" key={teacher.id}><div><strong>{teacher.display_name}</strong><span>{teacher.telegram_username ? `@${teacher.telegram_username}` : "Контакт скрыт настройками профиля"}</span></div>{teacher.telegram_username && <a className="telegram-link" href={`https://t.me/${teacher.telegram_username}`} target="_blank" rel="noreferrer">Написать <Icon name="arrow" /></a>}</div>)}</div><footer><span>{match.learners_count > 1 ? `Ещё ${match.learners_count - 1} участник(а) хотят этому научиться` : "Ты уже можешь собрать первую встречу"}</span><button className="text-button" type="button" onClick={() => openEvents("create")}>Создать встречу <Icon name="arrow" /></button></footer></article>)}</div>}</div>
        <aside className="side-column"><section className="panel my-skills"><div className="section-heading"><div><div className="profile-kicker-row"><span className="kicker">Мой профиль</span><button className="profile-edit-button" type="button" onClick={() => setProfileEditing((value) => !value)} aria-label="Редактировать профиль" title="Редактировать профиль"><Icon name="edit" /></button></div><h2>Навыки</h2></div></div><div className="skill-group"><div className="skill-group-heading"><span><Icon name="teach" /> Могу научить</span><button className="icon-button bordered compact-plus" type="button" onClick={() => setEditorIntent("teach")} aria-label="Добавить навык, которому могу научить"><Icon name="plus" /></button></div><div className="chip-list">{groupedMySkills.teach.length ? groupedMySkills.teach.map((skill) => <SkillChip key={skill.id} skill={skill} removing={removeSkillMutation.isPending} onRemove={(item) => removeSkillMutation.mutate(item)} />) : <small>Пока ничего не добавлено</small>}</div></div><div className="skill-group"><div className="skill-group-heading"><span><Icon name="learn" /> Хочу научиться</span><button className="icon-button bordered compact-plus" type="button" onClick={() => setEditorIntent("learn")} aria-label="Добавить навык, которому хочу научиться"><Icon name="plus" /></button></div><div className="chip-list">{groupedMySkills.learn.length ? groupedMySkills.learn.map((skill) => <SkillChip key={skill.id} skill={skill} removing={removeSkillMutation.isPending} onRemove={(item) => removeSkillMutation.mutate(item)} />) : <small>Пока ничего не добавлено</small>}</div></div>{removeSkillMutation.isError && <div className="inline-error">Не удалось убрать навык.</div>}</section></aside></section>
      <section className="community-section"><div className="section-heading"><div><span className="kicker">Карта сообщества</span><h2>Чем живёт SkillPeer21</h2></div><span className="muted-note">Сначала самые активные темы</span></div><div className="skill-stat-grid">{dashboard.skills.slice(0, 8).map((skill) => { const total = skill.teachers_count + skill.learners_count || 1; const teacherShare = Math.round((skill.teachers_count / total) * 100); return <article className="skill-stat-card" key={skill.skill_id}><div><h3>{skill.skill_name}</h3><span>{total} связей с участниками</span></div><div className="balance"><div className="balance-bar"><span style={{ width: `${teacherShare}%` }} /></div><div className="balance-labels"><span><b>{skill.teachers_count}</b> могут научить</span><span><b>{skill.learners_count}</b> хотят</span></div></div></article>; })}</div></section>
    </main>{communityView && <CommunityModal view={communityView} dashboard={dashboard} onClose={() => setCommunityView(null)} />}</div>;
}

function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(getAccessToken()));
  const queryClient = useQueryClient();
  function logout() { clearTokens(); queryClient.clear(); setAuthenticated(false); }
  if (!authenticated) return <LoginScreen onLoggedIn={() => setAuthenticated(true)} />;
  return <DashboardPage onLogout={logout} />;
}

export default App;