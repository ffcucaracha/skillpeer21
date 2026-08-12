import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, clearTokens, getAccessToken, saveTokens, type Skill } from "./api";

type IconName = "spark" | "people" | "book" | "teach" | "learn" | "plus" | "logout" | "arrow";

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
  };
  return <svg {...common} aria-hidden="true">{paths[name]}</svg>;
}

function LoginScreen({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: () => api.login(login, password),
    onSuccess: (tokens) => {
      saveTokens(tokens);
      onLoggedIn();
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <main className="login-page">
      <section className="login-brand">
        <div className="brand-mark">21</div>
        <span>School 21 community</span>
        <h1>Навыки становятся сильнее, когда ими делятся.</h1>
        <p>SkillPeer21 соединяет тех, кто хочет научиться, с теми, кто готов передать свой опыт.</p>
        <div className="brand-points">
          <span><Icon name="spark" /> Находи совпадения по интересам</span>
          <span><Icon name="people" /> Учись у равных и учи сам</span>
        </div>
      </section>
      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div>
            <span className="kicker">Добро пожаловать</span>
            <h2>Войти в SkillPeer21</h2>
            <p>Используй логин и временный пароль, выданные администратором.</p>
          </div>
          <label>
            Логин
            <input value={login} onChange={(event) => setLogin(event.target.value)} autoComplete="username" required />
          </label>
          <label>
            Пароль
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required />
          </label>
          {mutation.isError && <div className="error-message">Не удалось войти. Проверь логин и пароль.</div>}
          <button className="primary-button" type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Входим…" : "Войти"}
            {!mutation.isPending && <Icon name="arrow" />}
          </button>
        </form>
      </section>
    </main>
  );
}

function SkillPicker({ skills, onDone }: { skills: Skill[]; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [selectedSkillId, setSelectedSkillId] = useState<number | null>(null);
  const [intent, setIntent] = useState<"teach" | "learn">("learn");

  const createMutation = useMutation({ mutationFn: () => api.createSkill(name) });
  const linkMutation = useMutation({
    mutationFn: ({ skillId, skillIntent }: { skillId: number; skillIntent: "teach" | "learn" }) => api.addSkillIntent(skillId, skillIntent),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["skills"] }),
        queryClient.invalidateQueries({ queryKey: ["my-skills"] }),
      ]);
      setName("");
      setSelectedSkillId(null);
      onDone();
    },
  });

  async function addNewSkill() {
    if (!name.trim()) return;
    try {
      const skill = await createMutation.mutateAsync();
      await linkMutation.mutateAsync({ skillId: skill.id, skillIntent: intent });
    } catch {
      // Error state is rendered below.
    }
  }

  async function addExistingSkill() {
    if (!selectedSkillId) return;
    try {
      await linkMutation.mutateAsync({ skillId: selectedSkillId, skillIntent: intent });
    } catch {
      // Error state is rendered below.
    }
  }

  const busy = createMutation.isPending || linkMutation.isPending;
  const error = createMutation.error?.message || linkMutation.error?.message;

  return (
    <div className="skill-editor">
      <div className="intent-toggle" role="group" aria-label="Тип навыка">
        <button type="button" className={intent === "learn" ? "active" : ""} onClick={() => setIntent("learn")}>
          <Icon name="learn" /> Хочу научиться
        </button>
        <button type="button" className={intent === "teach" ? "active" : ""} onClick={() => setIntent("teach")}>
          <Icon name="teach" /> Могу научить
        </button>
      </div>
      <div className="editor-grid">
        <label>
          Выбрать из каталога
          <select value={selectedSkillId ?? ""} onChange={(event) => setSelectedSkillId(event.target.value ? Number(event.target.value) : null)}>
            <option value="">Выбери навык</option>
            {skills.map((skill) => <option key={skill.id} value={skill.id}>{skill.name}</option>)}
          </select>
        </label>
        <button className="secondary-button" type="button" onClick={addExistingSkill} disabled={!selectedSkillId || busy}>Добавить</button>
      </div>
      <div className="or-divider"><span>или добавить новый навык</span></div>
      <div className="editor-grid">
        <label>
          Новый навык
          <input placeholder="Например, фотография" value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <button className="secondary-button" type="button" onClick={addNewSkill} disabled={!name.trim() || busy}>Создать</button>
      </div>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [showSkillEditor, setShowSkillEditor] = useState(false);
  const userQuery = useQuery({ queryKey: ["me"], queryFn: api.me });
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const skillsQuery = useQuery({ queryKey: ["skills"], queryFn: api.skills });
  const mySkillsQuery = useQuery({ queryKey: ["my-skills"], queryFn: api.mySkills });

  const loading = userQuery.isLoading || dashboardQuery.isLoading || skillsQuery.isLoading || mySkillsQuery.isLoading;
  const failed = userQuery.isError || dashboardQuery.isError || skillsQuery.isError || mySkillsQuery.isError;

  const groupedMySkills = useMemo(() => {
    const result = { teach: [] as string[], learn: [] as string[] };
    for (const skill of mySkillsQuery.data ?? []) result[skill.intent].push(skill.skill_name);
    return result;
  }, [mySkillsQuery.data]);

  if (loading) return <main className="center-state"><div className="loader" /><p>Собираем твоё комьюнити…</p></main>;
  if (failed || !userQuery.data || !dashboardQuery.data) {
    return <main className="center-state"><h2>Не удалось загрузить дашборд</h2><button className="primary-button" onClick={onLogout}>Войти заново</button></main>;
  }

  const user = userQuery.data;
  const dashboard = dashboardQuery.data;
  const firstName = user.display_name.split(" ")[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="logo-row"><div className="brand-mark small">21</div><div><strong>SkillPeer21</strong><span>peer-to-peer learning</span></div></div>
        <nav>
          <a className="active" href="#dashboard"><Icon name="spark" /> Главная</a>
          <a href="#skills"><Icon name="book" /> Навыки</a>
          <a href="#matches"><Icon name="people" /> Совпадения</a>
        </nav>
        <div className="sidebar-profile">
          <div className="avatar">{user.display_name.slice(0, 2).toUpperCase()}</div>
          <div><strong>{user.display_name}</strong><span>{user.role === "admin" ? "Администратор" : "Участник School 21"}</span></div>
          <button className="icon-button" type="button" onClick={onLogout} aria-label="Выйти"><Icon name="logout" /></button>
        </div>
      </aside>

      <main className="dashboard" id="dashboard">
        <header className="dashboard-header">
          <div><span className="kicker">School 21 · обмен опытом</span><h1>Привет, {firstName}.</h1><p>Посмотри, чему сегодня можно научиться у своих пиров.</p></div>
          <button className="primary-button compact" type="button" onClick={() => setShowSkillEditor((value) => !value)}><Icon name="plus" /> Добавить навык</button>
        </header>

        {showSkillEditor && <section className="panel editor-panel"><div className="section-heading"><div><span className="kicker">Мой профиль</span><h2>Добавить навык</h2></div><button className="text-button" onClick={() => setShowSkillEditor(false)}>Закрыть</button></div><SkillPicker skills={skillsQuery.data ?? []} onDone={() => setShowSkillEditor(false)} /></section>}

        <section className="metric-grid" aria-label="Статистика сообщества">
          <article className="metric-card accent"><span className="metric-icon"><Icon name="people" /></span><div><span>Участников</span><strong>{dashboard.summary.members_count}</strong><small>внутри сообщества</small></div></article>
          <article className="metric-card"><span className="metric-icon"><Icon name="book" /></span><div><span>Навыков</span><strong>{dashboard.summary.skills_count}</strong><small>в общем каталоге</small></div></article>
          <article className="metric-card"><span className="metric-icon"><Icon name="teach" /></span><div><span>Готовы учить</span><strong>{dashboard.summary.teaching_offers_count}</strong><small>предложений опыта</small></div></article>
          <article className="metric-card"><span className="metric-icon"><Icon name="spark" /></span><div><span>Совпадений</span><strong>{dashboard.summary.matched_learning_goals_count}</strong><small>целей уже с преподавателем</small></div></article>
        </section>

        <section className="content-grid" id="matches">
          <div className="main-column">
            <div className="section-heading"><div><span className="kicker">Твои совпадения</span><h2>Есть у кого научиться</h2></div><span className="count-badge">{dashboard.matches.length}</span></div>
            {dashboard.matches.length === 0 ? (
              <div className="empty-state panel"><span className="empty-icon"><Icon name="spark" /></span><h3>Пока нет прямых совпадений</h3><p>Добавь то, чему хочешь научиться. Как только кто-то отметит этот навык как «могу научить», совпадение появится здесь.</p><button className="secondary-button" onClick={() => setShowSkillEditor(true)}>Добавить интерес</button></div>
            ) : (
              <div className="match-list">
                {dashboard.matches.map((match, index) => (
                  <article className={`match-card ${index === 0 ? "featured" : ""}`} key={match.skill_id}>
                    <div className="match-top"><div><span className="match-label">Хочу научиться</span><h3>{match.skill_name}</h3></div><span className="teacher-count">{match.teachers.length} {match.teachers.length === 1 ? "пир может научить" : "пира могут научить"}</span></div>
                    <div className="teacher-stack">
                      {match.teachers.slice(0, 3).map((teacher) => (
                        <div className="teacher-row" key={teacher.id}><div className="avatar soft">{teacher.display_name.slice(0, 2).toUpperCase()}</div><div><strong>{teacher.display_name}</strong><span>{teacher.telegram_username ? `@${teacher.telegram_username}` : "Контакт скрыт настройками профиля"}</span></div>{teacher.telegram_username && <a className="telegram-link" href={`https://t.me/${teacher.telegram_username}`} target="_blank" rel="noreferrer">Написать <Icon name="arrow" /></a>}</div>
                      ))}
                    </div>
                    <footer><span>{match.learners_count > 1 ? `Ещё ${match.learners_count - 1} участник(а) хотят этому научиться` : "Ты уже можешь собрать первую встречу"}</span><button className="text-button">Создать встречу <Icon name="arrow" /></button></footer>
                  </article>
                ))}
              </div>
            )}
          </div>

          <aside className="side-column">
            <section className="panel my-skills" id="skills">
              <div className="section-heading"><div><span className="kicker">Мой профиль</span><h2>Навыки</h2></div><button className="icon-button bordered" onClick={() => setShowSkillEditor(true)}><Icon name="plus" /></button></div>
              <div className="skill-group"><span><Icon name="teach" /> Могу научить</span><div className="chip-list">{groupedMySkills.teach.length ? groupedMySkills.teach.map((name) => <span className="chip teach" key={name}>{name}</span>) : <small>Пока ничего не добавлено</small>}</div></div>
              <div className="skill-group"><span><Icon name="learn" /> Хочу научиться</span><div className="chip-list">{groupedMySkills.learn.length ? groupedMySkills.learn.map((name) => <span className="chip learn" key={name}>{name}</span>) : <small>Пока ничего не добавлено</small>}</div></div>
            </section>
          </aside>
        </section>

        <section className="community-section">
          <div className="section-heading"><div><span className="kicker">Карта сообщества</span><h2>Чем живёт SkillPeer21</h2></div><span className="muted-note">Сначала самые активные темы</span></div>
          <div className="skill-stat-grid">
            {dashboard.skills.slice(0, 8).map((skill) => {
              const total = skill.teachers_count + skill.learners_count || 1;
              const teacherShare = Math.round((skill.teachers_count / total) * 100);
              return <article className="skill-stat-card" key={skill.skill_id}><div><h3>{skill.skill_name}</h3><span>{total} связей с участниками</span></div><div className="balance"><div className="balance-bar"><span style={{ width: `${teacherShare}%` }} /></div><div className="balance-labels"><span><b>{skill.teachers_count}</b> могут научить</span><span><b>{skill.learners_count}</b> хотят</span></div></div></article>;
            })}
          </div>
        </section>
      </main>
    </div>
  );
}

function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(getAccessToken()));
  const queryClient = useQueryClient();

  function logout() {
    clearTokens();
    queryClient.clear();
    setAuthenticated(false);
  }

  if (!authenticated) return <LoginScreen onLoggedIn={() => setAuthenticated(true)} />;
  return <Dashboard onLogout={logout} />;
}

export default App;
