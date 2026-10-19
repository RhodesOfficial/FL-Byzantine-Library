# G1.3 连续机制与共同随机映射证书 v1

## 1. 身份、目标与冻结
- 开工HEAD=`c9ac704e63a4f86f53678a3042bdb5b94d15cf2d`；任务基准`71ab9b4da902052cf5f1db8fcb7fcc3812a03560`为其父提交，包含裁决v6及合同§六ε补录的HEAD锁定不变。
- [裁决v6§1–2](DIRECTION_A_G1_3_ADJUDICATION_v6.md)：B局部2/3/4/5/7 PASS、1/6 FAIL；220类盲量接受，保护/计量FAIL独立保留，完整G1.3未通过。
- 固定目标是封存binary32完整weight(C,128)+bias(C)的精确实数向量；下文不外推理想梯度。B字节、旧包、源码、合同及ROLE保持原状。
- 权威ε定位：`71ab9b4:artifacts/direction_a/phaseG1_3_B_d6_v1/V1/blind_results.json`，按`ref`取`mean_tau[group]=[l,w]`，θ_ref,group=(int(l,16)+int(w,16))/2^192；下表完整标明八字段，l/w沿裁决v6§2，不再读盲量。

|ref|group|精确门槛的字段|
|---|---|---|
|A-backbone-CIFAR10-s2026101321-r0040-v1|all|该ref.mean_tau.all的Q192上端|
|A-backbone-CIFAR10-s2026101321-r0040-v1|tail|该ref.mean_tau.tail的Q192上端|
|A-backbone-CIFAR10-s2026101321-r0080-v1|all|该ref.mean_tau.all的Q192上端|
|A-backbone-CIFAR10-s2026101321-r0080-v1|tail|该ref.mean_tau.tail的Q192上端|
|A-backbone-CIFAR100-s2026101322-r0040-v1|all|该ref.mean_tau.all的Q192上端|
|A-backbone-CIFAR100-s2026101322-r0040-v1|tail|该ref.mean_tau.tail的Q192上端|
|A-backbone-CIFAR100-s2026101322-r0080-v1|all|该ref.mean_tau.all的Q192上端|
|A-backbone-CIFAR100-s2026101322-r0080-v1|tail|该ref.mean_tau.tail的Q192上端|

十进制仅展示，不参加严格比较；已用ε上端包络的τ宽度不再扣一次。四参考×all/tail须全部成立，不另设逐类门槛。

## 2. 连续与格点的有限概率误差（静态可证）
源码依据：本HEAD的`direction_a/formal_f.py:probability/outcome`、`direction_a/formal_f_policy.py:invite`、`scripts/run_direction_a_formal_f.py:369–398`；这是源码推导，未执行函数、读取真实p或F事件。
令N=2^53（随机格点数，区别于类分母N_c），q=8/20，α=9/10，β=1/20，δ=16/5模拟单位；0<L_i≤1、s_i∈{1,4}为固定外生参数。
时长T_i=s_i L_i(1/4+3U_j/2)，x_i=(δ/(s_i L_i)−1/4)/(3/2)，f_i=clip(x_i,0,1)。δ、T用模拟时间单位，L、s、x、概率及η均无量纲。
连续分布模型：每attempt均匀无放回20选8，邀请集独立于各端在线/掉线/jitter三组独立U[0,1)变量；不同attempt的独立性是模型假设，不是固定PRNG种子的定理。
事件为J'_ti=I_ti·1(U_o<α)·1(U_d≥β)·1(U_j≤x_i)，故p'_i=q α(1−β) f_i。deadline含等号；连续单点概率0，x=0时该因素概率0。
格点模型令K_o,K_d,K_j各均匀于{0,…,N−1}且按模型独立，U^g=K/N，同一邀请模型；J_ti按相同不等式定义。
严格在线格点数A=ceil(Nα)，存活格点数H=N−ceil(Nβ)，deadline格点数K_i=clip(floor(Nx_i)+1,0,N)，p_i=q A H K_i/N^3。
取整理由：k<Nα有ceil(Nα)项；k≥Nβ有N−ceil(Nβ)项；k≤Nx有floor(Nx)+1项并截断。x<0取0，x≥1取N，x=0取1，整数Nx也保留等号点；均与源码一致。
于是0≤A/N−α<1/N，0≤(1−β)−H/N<1/N，|K_i/N−f_i|≤1/N；最后一个≤在x=0或格点deadline处可取等号。
对[0,1]中三因子用abc−a'b'c'=(a−a')bc+a'(b−b')c+a'b'(c−c')，逐项取绝对值得|r_i−r'_i|≤3/N。
**全部源可用η_i=3q/N=6/(5·2^53)**；与参考、速度场景、类、梯度及实际L值无关，只依赖上述域和事件定义。无需把2e−6或经验频率代入。
由δ/(sL)≥4/5得x≥11/30，p'_i≥627/5000，p_i≥627/5000−η_i>0；是全域支持证明，不是对真实主p的读取。
类内Σa_i=1时t=Σa_iη_i=η，Z≥627/5000−η>η=t（有理交叉相乘可验）；故连续正分母在该模型和有效域下静态闭合，无需盲p实测。若C绑定域/身份未验，此结论仍有条件。
实现事实与分布假设分开：源码精确有理计算保证给定格点的映射；固定seed的PCG输出是确定值，不能从函数名推出统计独立或连续真随机性。

## 3. 四流消费与耦合（分布可证，固定路径未闭合）
F现有结构源码仅生成S=2026102300；数值规范§4的三seed S=2026102300/2026102400/2026102500是未来配对定义，不能称已生成三条连续轨迹。

|流|底层输出及映射|消费/边界与共同对象|
|---|---|---|
|PCG64(S+1)|每attempt `choice(20,8,replace=False)`，随后排序|原20端无放回，一次完整集合共同复用；invite只验证8个唯一注册ID；不按在线情况补邀|
|PCG64(S+2)|`integers(0,N,size=20,dtype=int64)`的K_o|每attempt先生成全20端，按ID取值；K_o/N<α|
|PCG64(S+3)|同形状K_d|同上，K_d/N≥β；未邀/离线也已消费，不条件跳抽|
|PCG64(S+4)|同形状K_j|同上，K_j/N≤x_i；不同场景/参考只改固定x，不重新消费|

每attempt调用顺序为邀请、在线20、掉线20、jitter20，共32 attempts；step只索引计划，不再抽数；round只有返回非空才增加，attempt仍推进。排序不改变集合或边际q。
无放回意味着同attempt两端邀请联合概率8·7/(20·19)，不等于q²；后续求和/并集界不使用端间独立性，跨参考/场景复用也不是新增重复。
版本定位：封存`phaseG1_1_formal_F_resume_v1/plans.json#numpy_version`仅定向提取为1.26.4，当前安装`E:/anaconda3/Lib/site-packages/numpy/version.py`也为1.26.4；未读取计划抽样值或事件。
[NumPy 1.26 integers原文](https://numpy.org/doc/1.26/reference/random/generated/numpy.random.Generator.integers.html)定义半开整数区间与离散均匀；[choice原文](https://numpy.org/doc/1.26/reference/random/generated/numpy.random.Generator.choice.html)定义默认均匀及无放回。
[兼容性原文](https://numpy.org/doc/1.26/reference/random/compatibility.html)把复现限制到相同build/环境/调用参数与序列；版本号不证明build身份，更不提供与`random()`连续U共享的逐比特映射或跨流数学独立证明。
**可证的分布耦合**：共享邀请集；对每个模型格点K另配独立V∼U[0,1)，令U'=(K+V)/N。于是U'均匀连续且floor(NU')=K；三流/attempt按模型共同构造，J、J'沿§2映射。
每在线/存活/jitter布尔因子只可能在其阈值所在格内失配，每项概率≤1/N；用并集界及邀请独立性，P(J'_ti≠J_ti)≤3q/N=η_i。边际差≤失配概率，这一上界来自特定耦合而非边际η本身。
对ζ_sc=(1/32)Σ_tΣ_i a_ic|J'_ti−J_ti|，线性期望给Eζ_sc≤Σa_iη_i=t_c；不需20端或32次独立。至多可由Markov写P(ζ>h)≤t/h，h>0，不能宣称三个固定seed已满足该概率事件。
**首个路径缺口**：F只定义格点K，没有定义附加V或底层连续U；给定同seed并不唯一决定上述连续轨迹。把相同seed另喂`random()`也没有同位消费证明，不能认定是该耦合。
反例一（边际不足）：U均匀，J=1(U<1/2)、J'=1(U≥1/2)，边际差0而失配1；η=0并不迫使ζ=0。
反例二（期望不足）：在deadline边界格K_j=floor(Nx_i)且K_j/N≤x_i<1时，选V>Nx_i−K_j可使格点按时而连续超时；该稀有事件可出现在某条固定路径上，不能用Eζ替代路径ζ。
有限补证方式：优先另派只读边界证书，绑定原计划身份及L/s的精确有理值，逐seed/attempt/ID验证所有已邀端的格点所在区间不跨阈值；若不跨则对任意V路径失配0，不需生成连续随机数。
具体保守边界指示B_ti：在线K_o=floor(Nα)、存活K_d=floor(Nβ)、或0≤x_i<1且K_j=floor(Nx_i)三者的并集（整数阈值可进一步消去不可能项）；|J'−J|≤I_ti B_ti，ζ≤mean_32Σa_i I_ti B_ti≤1。
该有限表仍需获读取/计算授权及前置保护，本单不读计划值、不赋ζ实数；若出现边界，仅报告上界或另审连续映射定义，不追加seed/重抽。均匀对照deadline恒通过，只有在线/存活边界，仍需自身ζ_0证书。

## 4. 八项主裁决依赖与未来C输入
以下沿[准入方案§2–3](DIRECTION_A_G1_3_MEASUREMENT_READINESS_v1.md)和[数值规范§3–4](DIRECTION_A_G1_3_NUMERICAL_SPEC_v1.md)，不替换阈值/统计。M=max‖g_i‖，S=Σa_i‖g_i‖，A=‖d‖，z_c=Z−t。
|链条|推导/消费方式|静态状态或未来输入|
|---|---|---|
|η→解析变化|Σ|b'−b|≤2t/z_c，δ_d≤2Mt/z_c，δ_ρ≤δ_d/S_−|η及模型内Z>t已证；C核域、Z区间和S_−>0，再求数值上端|
|方向隔离零|A_−>δ_d时A'>0，δ_u≤2δ_d/(A_−−δ_d)|C需A区间；未隔离不得把方向变化设0|
|ζ→随机均值|δ_X,s≤M[ζ_s/z_c+t/(Z z_c)]|固定32次ζ未证；t只约束期望，不能代ζ|
|均匀对照|p0=qα_g h_g，p'_0=qα(1−β)，η0≤3q/N；p_c=p0−η0>0；δ_X0,s≤M[ζ0,s/p_c+η0/(p0 p_c)]|同流邀请/在线/存活、K=N；p0正下界同§2，ζ0待证|
|投影变化|δ_W,s≤δ_X,s+δ_X0,s；R_W≤M(1/Z+1/p0)；δ_P,s≤(δ_W,s+δ_uR_W)/S_−|C绑定相同g/a/G、方向及主/对照，另加未纳入的区间算术项|
|固定macro→端点|每类误差按固定分母均值；seed误差e_s给端点界mean e_s+√(722/39)·√Σe_s²/√6+端点运算界|全类10/100、尾4/34；3seed×32不改，误差不以独立性缩小|
|解析包含|同对象L−E_I−E_R≤ρ̂≤U+E_I+E_R（含等号）|格点包含用格点误差；若转连续，双方相应外包，不混用两个目标|
|两种严格下界|ρ̂−E_R−E_cont,analytic>θ；L−E_I−E_cont,projection>θ|每ref/group均成立，八项交集；解析连续项与路径投影项分开|

X=ΣaJg/Z，X0=ΣaJ0g/p0。上式分母拆分用mean ΣaJ≤1及Σa‖g‖≤M，方向拆分用u'W'−uW=u'(W'−W)+(u'−u)W；故无需端/类独立。
端点界由均值误差≤mean e_s、中心化算子范数≤1与范数反三角不等式得|δSD|≤√Σe_s²/√2，再乘t/√3；t=√(722/39)及运算均外包。近似95%覆盖条件仍沿原规范，不升级为八项同时95%。
结构零：S=0须逐坐标证明所有g=0，定义ρ=τ=u=0并保留macro分母；仅区间碰零则不可辨。单源/同源解析d=D=τ=0；如方向可被概率扰动改变，不因格点d=0套非零方向式。
所有正来源同p时b=a、解析d=0，数值区间应含0；均匀随机对照不要求每seed投影零。结构同源下X仍可随机波动，不能把向量残差补零。
任何必需项null/不可辨传到相应macro与严格通过项，不能删类；精确ρ=0而θ≥0本就不能满足严格正下界。S结构零的数值约定不能变成通过证据。
不重复扣项：ε上端已含τ宽度；E_R/E_I若已含某算术/连续项，严格式该项只扣一次，需C列误差对象清单；路径δ_P不能用解析δ_ρ替代。
Ri/vi另列：固定封存目标E_i=0；历史差异需逐源Ri绑定才有√(129C)·2e−6 Ri，理想外推还需vi；二者仍null，不纳入本目标也不声称理想CE结论。
未来C至少需：原计划/build/源码身份、三seed共同映射或边界表、真实格点p及Z区间、B逐类S/M/τ绑定、A/d与方向区间、均匀p0/ζ0、各seed配对投影、固定macro及端点误差图；均须另派完整保护周期。
本证书闭合有限η及条件传播；未闭合固定路径ζ/方向/主八项数值，故完整G1.3仍未通过。本单纸面缺口定位满足文档范围，不开放C/G2或B复跑。
