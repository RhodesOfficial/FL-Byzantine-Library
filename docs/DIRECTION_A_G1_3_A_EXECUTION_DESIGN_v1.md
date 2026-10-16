# G1.3 完整A静态执行设计 v1（待审，未实施）

依据：09bf82d的NUMERICAL_SPEC（下称N）§1–5、REMAINING_PLAN（下称R）§1–6，当前任务/两ROLE/STATE，候选PREREGISTRATION_PLAN_v1（下称P）及IMPLEMENTATION_SPEC、ff31cff原A六判据。此稿不替换科学定义；动作费用见同名A_BUDGET_PROPOSAL_v1（下称预算）。
唯一推荐：改造现有五个源码/测试的共享外层，执行一个“定向元数据→独立合成→B工作表→本轮封存”工作图；最多两轮验证及一次独封，成功即交审。路径、授权版本及下述上限须另单冻结，本单程序启动0。

## 1. 动作图及输入边界
编号是未来reserve/日志键；V1/V2独立计费，闭合包只作为只读前驱，不改写c35ae78成功包，不伪造其失败状态；新账用predecessor与carry_once引用旧累计。
|动作/顺序|入口、输入、输出及原A判据映射|
|---|---|
|A00→A01|现有outer.ps1先启单一累计监督器，装载审定静态额度，再受保护读前驱ledger；旧风险、实耗、未知、关闭项一次承接。映射原4/6。|
|A01→A02|outer读五源码合计≤256 KiB，PS两文件解析，Python三文件compile缓存；使用E:\anaconda3\python.exe -B -c固定引导，不让解释器另读主脚本。语法→CPU→续接探针共一工程轮，两个子进程均接外层。映射原3/4。|
|A02→A03|15份元数据只读一次，原字节哈希一次；字段定向抽取、类/源遍历先留额，输出input_index及四参考绑定。真实p/消息/模型/事件读取与计算0。映射原1。|
|A03→A04|只用本稿人工向量/有理概率及固定人工mask，顺序运行92调用；被测区间内核与独立手算oracle分别留额；新守卫接口回归见§5。映射原2/3/4。|
|A04→A05|从A02的D/G字段形成逐类B工作量、盲字段合同及缺项；F/V/M字段只作A定位，不传B。映射原2/5。|
|A05→A06|写bundle和checkpoint，finally无论成功/失败都走本轮S；异常签名、已完成/部分/未开始逐项保留，禁止用非空字典代完成。映射原3/4/6。|
|A06→结束或V2|本轮独立回读后才报状态；无新增结果工程问题且剩额足够才修复复验；新科学结果/身份不符/保护失效等按ROLE封存。V2重做的读取/计算/封存均再计，已完整真实头从不重训。|
|A07（独封I+S）|仅完整可核前驱且明确派单才进入seal.ps1委托同一outer；单列第3工程，无语法/CPU重验，重读证据/输入并重新哈希照计；不替代V1/V2的finally。|
规则/状态/任务读取与交接/Git属于有限启动准备，另账；不要求先启动A00才能读到规则。受限读取、语法、CPU、子进程及封存全部必须先有A00，不借准备例外运行。

## 2. 元数据与四参考schema
白名单沿现行g1_3_preparation.py的WHITELIST：D两数据集各counts.json/info.json（4）；G/full的preregistration/reference_acceptance/artifact_hashes/archive_verification及backbone manifest（5）；F/resume的mechanism/input_checks/preregistration/replay_checks（4）；V/speed_assignments与M/measurements各1。首次15份327534 B仅引用R§1/eaecc95，未来逐文件长度仍null；总原文硬限1 MiB，不扩大名单找替代。
每输入行`{action_id,commit,path,raw_bytes,raw_sha256,git_object,field_locators,checks,status,missing}`，路径≤256 ASCII字节、SHA固定64、commit40；字段缺失/长度越界即精确报对象，不扫描消息或979366 B的G measurements。历史文本身份只比Git对象或仅换行归一，不能把旧raw哈希充归一哈希。
D提取n_ic(20×C)、N_c、标签双射、任务/split身份；验证非负整数≤2^31−1、每类N>0、20端一致及加总，按N降序/ID升序分全/中/尾，尾分母4/34；组ID沿P§1引用，实际排序必须核对，不先假定类号范围。n=0不进正来源，缺失不补0。
G提取四参考checkpoint_path/state_sha256/task_identity/training_progress及每端/类分母、消息locator、封存SHA的索引绑定；四ID按P§1的C10 seed2026101321及C100 seed2026101322、各r0040/r0080，各20端，C=10/100。A验索引相互一致，不验二进制内部字段。
F/V定位机制版本、四流/原消费顺序、三速度各10端1/10端4；M只定位rows[].b_seconds/L及B_seconds，字段路径来自R§1、原始键待A02确认，值不得参与真实p计算；缺路径即missing，不计算费用或新机制数值。
`bindings[4]`逐项输出dataset/ref/task/checkpoint/state/20端/分母/消息SHA来源及`metadata_binding_status`；另列`binary_qualification=NOT_RUN`。B才逐消息核验SHA、dtype=float32、weight(C,128)+bias(C)、有限性及分母/来源；A不宣称验证了封存梯度值。

## 3. 唯一区间算法与不可辨出口
对象/公式及误差归属严格沿N§1–4。数值内核选Q192定点区间：端点为整数/2^192，每次+−×÷都用整数floor/ceil向外包围；无硬件float中间舍入假设，输入float32由符号/指数/尾数精确解码，包括次正规及±0。人工输入|g|≤2^16、m≤3、h=129C，正counts≤2^31−1、p有理分母≤2^64；真实B范围待二进制资格另冻。
运算顺序：检查→有理a=n/N与p→Z=Σap→b=ap/Z→G=Σag及d=Σ(b−a)g（源ID顺序，坐标weight行优先后bias）→各源平方和/sqrt→S→每源对距离/D/RMS→A、ρ、τ、目标比→方向→逐attempt的X/X0→mean32→Y/Y0/P→固定macro→三seed区间。另以精确有理权重和二进制输入逐坐标认证G/d是否严格零（位宽同限），解决09抵消不能由浮点区间判零的问题；该认证的运算/遍历已入M。所有完整头坐标均参与，N精确，不以返回数替代。
区间乘法取四端点极值；除数区间含0即UNRESOLVED。sqrt([l,u])在l≥0时取isqrt(l·2^192)、ceil_isqrt(u·2^192)，均以平方比较证实；二分实现每根≤4096步。负下端只允许由已知非负平方和截到0，其他负开方拒绝。
任一中间整数含乘积/移位超4096位先拒绝`PRECISION_CAP`；sqrt操作先检查移位位数。Q192以下非零输入包入[0,2^−192]，不flush为结构零；无浮点溢出，显示float64溢出/次正规只影响可选展示，不能改变端点或判定。禁止自动加精度、加常数或重算。
独立oracle不调用metric、norm或区间内核：采用N§5手算有理系数/根式，独立整数平方比较核证被测上下端夹住真值；多根式用2^−256网格的独立有理包围证明包含，不能仅检查两区间相交。oracle与内核分别计费；位数不足/无法决定包含或严格关系时UNRESOLVED，不能容差判PASS。
全源逐坐标精确0才是结构零：S=A=ρ=τ=0、u=0，Y=Y0=P=0且向量残差0，A/‖G‖=null；该类仍占macro分母。非结构零而S下端≤0则必需比值/macro未完成。精确d=0但S>0时u=0、主投影0，仍返回X−G全向残差并另用非零固定方向测试；m=1/同源的D/τ=0，S照报。
N§2四误差各字段独立：封存目标源扰动因定义为0；历史差异√(129C)·2e−6·R_i及理想v_i未知保留；区间宽度给本对象算术误差；连续η项独立。按N§3传播d/S/ρ/τ/u/P，分母下端>0，B仅D/G及最坏权重/符号z_*,p_*，C才代入。
三seed先同seed差再macro，再μ/SD(ddof1)/t区间；t=√(722/39)用同一sqrt包围，端点误差与解析误差沿N§4，解析包含允许等号而两个下界严格>θ。结构零macro照计；缺类/不可辨不能删项。八项为四参考×all/tail，非同时95%。连续随机投影外推独立证明仍缺，标`continuous_projection_bound=null`并关闭对应通过项，不以解析界顶替。

## 4. 14组逐调用与独立预期
记M=metric、Pj=projection、Rj=受控替换、E=误差/可辨性、Bnd=概率界、S3=三seed配对、Ag=macro；表中每个分号子项是独立断言，共享一次返回的并列字段不重复调用。每行都在h=1290及12900各运行一次。
完整坐标嵌入：v=(1,…,1)、w=(1,−1,…,1,−1)，将N§5的(x,y)映成xv+yw；两向量正交且范数√h，故G/d/距离/残差及S/A乘√h，ρ/τ不变，固定方向用v/√h。所有坐标含bias均实际迭代；04另用递增坐标识别错序/漏行，非法形状不按短向量补零。
|组|每h调用及各子断言的独立预期（未执行）|
|---|---|
|01|M1：Q均匀p；a=b、d=A=ρ=0，S=√h、D=√(2h)、τ=√2/2；u零。|
|02|M1+Rj1：Q的G=(v+w)/2、d=(v−w)/4；正替换ΔG=(w−v)/2、范数/S=√2/2。|
|03|M1+Rj1：同Q；反替换ΔG=(v−w)/2、范数同02、对固定方向投影符号相反。|
|04|M2：4Q的S=4√h、A=√(2h)，ρ/τ不变；单源r_j=(j+1)/16384，j=0..h−1，‖r‖²=h(h+1)(2h+1)/(6·2^28)、G=r且d=0（逐坐标匹配）。|
|05|M1：单源n=2、g=3v+4w；G=g、S=5√h、d=D=ρ=τ=0。|
|06|M1：两同源3v+4w、非均匀p；S=5√h、d=D=ρ=τ=0。|
|07|M1+Pj1+Ag1：全零；各结构零字段及32次全返回投影/残差0，目标比null；与ρ=1/2的第二类作all macro=1/4，分母2。|
|08|M1：g=(v,−v)；G=0、d=v/2、S=√h、ρ=1/2、τ=1，目标比null且cancellation=true。|
|09|M1：三源v,w,(v+w)/2及p=(1/4,1/4,1/2)；Z=1/3、b=(1/4,1/4,1/2)、G=G_avail=(v+w)/2、d=0。|
|10|M1：δ=1/1024、g=(v,(1+δ)v)；S=(1+δ/2)√h、d=−δv/4、ρ=δ/(4+2δ)、τ=δ/(2+δ)；近同源标记用专用合成阈值D/S上包络，真实阈值不赋值。|
|11|M1+Pj2：Q；32次全空mask、固定v/√h给Y=Y0=−1/2、P=0、残差范数√(h/2)；空attempt列表拒绝。|
|12|M11+E1：N=0、无源、Z=0、p<0、p>1、NaN、+Inf、−Inf、weight形状错、bias形状错、dtype错各调用M拒绝；E输入Ŝ=E_S>0报UNRESOLVED且ρ不填0。|
|13|Bnd2+E1：a=(1/2,1/2),η=(1/16,1/16),M=1,Z=1/2给t=1/16、界2/7；Z=t拒绝；Ŝ=1,E_S=1/4,Â=1/2,E_A=1/8另项0给Eρ上界1/3。|
|14|M1+Pj2+S3七次+Ag3：均匀Q，固定非零方向全返回给Y0=1/2、残差(v+w)/2；解析u=0时P=0仍保留同一残差。S3依次验证[5,6,7]−[1,1,1]的μ=5/SD=1/I=5±t/√3且θ=1通过、θ=L严格FAIL、解析在I外FAIL、两seed拒绝、P=[1,1,1]且θ=1 FAIL、解析等于L包含、等于U包含；Ag三次分别对两类逐seed(1,3)给all=2、tail第二类=3，以及对预置七PASS/一FAIL的八项记录给交集FAIL（无嵌套S3重算）。|
每h总M24/Pj5/Rj2/E2/Bnd2/S3七/Ag4=46调用，两维共92；最大m=3、每投影主/对照各32attempt，不生成注册seed轨迹，人工mask固定全空/全返。逐断言status初始NOT_RUN；上述FAIL是预期被拒/严格门槛结果，测试验证该结果才为PASS。

## 5. 输出、守卫回归与B交界
统一UTF8紧凑JSON，无浮点NaN：`{schema,run_id,predecessor,carry_once,action_id,status,counters,used,reserved,unknowns,completed,partial,not_started,failures,inputs,bindings,assertions,B_requirements}`；端点用十进制整数+固定k，所有null带reason与next_action。used实耗与reserved风险不混；旧FAIL/null及D3/F/P关闭原值保留。
输出长度由有界字段推出：92调用每行≤8192 B（≤24区间×2端点×96字节及字段/状态/预期≤3584 B），≤14组头×512 B、4绑定×8192 B、15输入×4096 B、220类B行×2048 B、固定头/失败≤65536 B，合计≤1371136 B，bundle硬限2 MiB；字段端点不能96字节内表示则记录PRECISION_CAP而不截断。
各输出总容器≤2048、深度≤16；区间是扁平字段字符串lo:hi:k，每调用≤2容器、每B行≤3、每输入≤3、每绑定≤21，92×2+220×3+15×3+4×21+512账行+64哈希行+头/失败≤499=2048，不另嵌套逐坐标数组。路径256、枚举64、异常签名/根因各512 B；按UTF8真实字节限额，严禁无限traceback/原向量/metadata全文写入。checkpoint≤128 KiB、ledger≤256 KiB（≤512聚合动作行×384 B+65536 B头）、receipt≤16 KiB、manifest≤32 KiB（≤64哈希行×384 B+8192 B头）；具体写/回读见预算S表。
五类已成功守卫仅引用c35ae78/guard_v1的receipt/ledger；改造涉及外层授权/续接/字节上限/内核租额/末端回读，新回归只覆盖这五个改变入口的拒绝前零访问、嵌套部分扣账、子进程继承及小字节封存见证，合计预留32扫描；不独立重跑旧五类套件，不冒充92数值调用。
B输出逐类`{ref,c,N,m,h,pairs,source_coordinate_visits,pair_coordinate_visits,read/hash/copy_actions,lifetimes,operation_bound,time_bound,Windows_peak_bound,missing}`；A只从元数据列m≤20、h与工作图，不从真实向量计算τ。80消息62840948 B/最大1929208 B、1356源/220类沿P/G接收引用；A不复验这些二进制统计。
B读取/哈希80消息最多两遍：160文件读+160哈希扫描，字节125681896；两遍缓存哈希各另记扫描，解码每遍80、每参考类遍历每遍4、源遍历每遍220、对遍历每类m(m−1)/2，类/源/坐标循环显式相乘。maxΣm h≤20·(2·10·1290+2·100·12900)=52116000，maxΣpairs h≤190·2605800=495102000，不能用1356或220替代。
B每消息寿命：raw≤1929208→校验/解码storage（大小null，须有受限allocator）→按类packed float32→流式64/区间累加→释放；raw、storage、完整头、工作向量、序列化/哈希/失败缓存均列copy字节，当前解码开销/平台峰/秒null。D/G外s/L/p字段禁止进入B；参考尺度R_i/独立理想界v_i缺失保持null。
最小后续方案：先审本图及额度，仅派完整A的元数据+92合成+B符号工作表；B/C不开放。完整A原判5的真实平台时间/峰尚不能静态证明，另审一次盲D/G的B硬限测量（候选300秒、读128 MiB、写8 MiB、2048扫描、CPU512 MiB/Windows2 GiB，均未生效），包含导入/解码/失败/封存，发生新τ后异常不重算；未补齐则完整A仍FAIL，不另开任务清零。
