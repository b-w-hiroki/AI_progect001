const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.join(__dirname,'..');
const read=file=>fs.readFileSync(path.join(root,file),'utf8');
test('README links resolve inside the repository',()=>{
 for(const [,target] of read('README.md').matchAll(/\]\(([^)]+)\)/g)) {
  if(/^(https?:|#)/.test(target))continue;
  assert(fs.existsSync(path.join(root,target.split('#')[0])),target);
 }
});
test('documented review guard matches the workflow and avoids claiming setup is complete',()=>{
 const workflow=read('.github/workflows/code-review.yml');
 assert.match(workflow,/github.actor == github.repository_owner/);
 assert.match(workflow,/github.event.pull_request.draft == false/);
 assert.match(workflow,/github.event.pull_request.head.repo.full_name == github.repository/);
 assert.match(read('README.md'),/認証シークレットの有無・有効期限・契約の利用枠はコードからは確認できません/);
});
test('lab completion distinguishes cost authorization, verification and cleanup evidence',()=>{
 const doc=read('docs/lab-completion.md');
 for(const term of ['費用上限','対象コミット','未実行','apply','destroy','利用明細'])assert.ok(doc.includes(term),term);
});
