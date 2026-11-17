// 全局主题定义：模板中心、状态徽标、生成请求共用一份配置，
// 保证「选择主题 → 界面同步 → 生成应用」全链路一致。
export const THEMES = [
  { key: 'auto',        name: '智能选型', emoji: '🎯', desc: 'AI 根据内容主题自动匹配最佳风格', bg: 'linear-gradient(135deg,#667eea,#764ba2)', dots: ['#fff','#ffd'] },
  { key: 'tech-blue',   name: '科技蓝',   emoji: '🔷', desc: '深蓝底 + 电光蓝，玻璃拟态',       bg: 'linear-gradient(135deg,#0B1220,#1D4ED8)', dots: ['#3B82F6','#93C5FD'] },
  { key: 'biz-gold',    name: '商务黑金', emoji: '🏛️', desc: '炭黑 + 香槟金，衬线标题',         bg: 'linear-gradient(135deg,#111,#3a2f0b)',   dots: ['#C9A227','#E7C873'] },
  { key: 'fresh-green', name: '清新自然', emoji: '🌿', desc: '米白 + 森林绿',                   bg: 'linear-gradient(135deg,#F7F5EF,#2F6B4F)', dots: ['#2F6B4F','#86C99B'] },
  { key: 'warm-orange', name: '暖橙活力', emoji: '🍊', desc: '奶油白 + 珊瑚橙',                 bg: 'linear-gradient(135deg,#FFF8F0,#E8622C)', dots: ['#E8622C','#FFB380'] },
  { key: 'minimal',     name: '极简杂志', emoji: '📰', desc: '纯白 + 留白 + 一处强调色',         bg: 'linear-gradient(135deg,#fff,#e5e5e5)',   dots: ['#111','#E11D48'] },
  { key: 'dark-neon',   name: '暗黑霓虹', emoji: '🌃', desc: '深底 + 霓虹紫青渐变',             bg: 'linear-gradient(135deg,#0A0A12,#7C3AED)', dots: ['#A78BFA','#22D3EE'] },
]

export const themeName = (key) => THEMES.find(t => t.key === key)?.name || '智能选型'
export const themeEmoji = (key) => THEMES.find(t => t.key === key)?.emoji || '🎯'
