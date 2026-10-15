# 面向高机动飞行的旋翼升力建模与控制方法

陈泽昊 1,2 常彦春 1 刘干 1,2 杨丽英 1 周浩 1 张广玉 1 何玉庆 1

摘 要 高机动飞行中的动态来流会使静态升力映射失配, 导致旋翼实际升力偏离指令值. 为提高执行器层的升力预测与扰动抑制能力, 本文建立由多旋翼无人机运动状态到单旋翼轴向升力的机理模型, 并结合实测桨叶几何、翼型极线及非均匀诱导入流叶素模型计算升力在此基础上，提出以旋翼逆模型为前馈、以直接升力测量为反馈的复合控制方法 并搭建奖盘攻角和转台角速度可调的旋转试验台. 结果表明, 所建模型能够准确描述测试包线内的升力变化规律, 所提出的复合控制方法可有效抑制单旋翼台架上的强来流扰动.

关键词 多旋翼无人机, 高机动飞行, 升力反馈控制, 叶素动量理论

引用格式 【待填写作者与引用信息】

DOI 10.16383/j.aas.20xx.cxxxxxx 

# Rotor Thrust Modeling and Control for Aggressive Flight

Chen Ze-hao<sup>1,2</sup> Chang Yan-chun<sup>1</sup> Liu Gan<sup>1,2</sup> Yang Li-ying<sup>1</sup> Zhou Hao<sup>1</sup> Zhang Guang-yu<sup>1</sup> He Yu-qing 

Abstract Dynamic inflow during high-maneuverability flight can cause a mismatch in the static thrust mapping, resulting in the actual thrust of the rotor deviating from the commanded value. To improve thrust prediction and disturbance suppression capabilities at the actuator level, this paper establishes a mechanistic model that maps the motion state of a multirotor UAV to the axial thrust of a single rotor, and calculates thrust by combining measured blade geometry, airfoil polar curves, and a non-uniform induced inflow element model. Based on this, a composite control method is propose that uses a rotor inverse model as feedforward and direct thrust measurements as feedback. A rotating test bench with adjustable blade disk angle of attack and turntable angular velocity was constructed. The results show that the developed model can accurately describe the thrust variation patterns within the test envelope, and the composite control metho can efectively suppress strong on-flow disturbances on the single-rotor test bench. 

Key words Multirotor unmanned aerial vehicle, High-maneuverability flight, Thrust feedback control, Blade element momentum theory 

Citation 【待填写英文作者与引用信息】

近年来, 低空经济加速向规模化、常态化运行发展, 多旋翼无人机凭借垂直起降、定点悬停与机动灵活等优势, 已成为应急救援、基础设施巡检和复杂环境作业的重要装备 [1,2]. 随着任务空间由开阔、低速场景拓展至城市障碍物密集区域, 无人机需要在其中敏捷穿梭, 即需要在快速姿态变化条件下保持稳定飞行. 在此类高机动工况下, 旋翼承受显著的动态来流扰动, 使飞控控制指令对应的实际升力偏离标称值, 进而影响机体姿态与位置控制的精度与稳定性.

现有多旋翼飞控通常依据静态标定得到的升力控制量映射, 将控制分配器输出的期望升力转换为电机控制指令. 该映射在近悬停与弱扰动条件下可近似表示为转速（或归一化控制量）的二次函数, 但其参数隐含了特定来流、桨盘姿态与推进系统状态.当无人机快速前飞、转弯或翻转时, 旋翼局部来流的速度与方向同时改变, 桨盘内轴向与面内速度分量高速变化, 从而改变叶素入流角、有效迎角及气动力分布. 由此产生的升力偏差首先出现在执行器层, 而传统控制架构通常需待机体姿态或位置误差形成后才能间接修正, 作用链路较长, 难以及时抑制旋翼层面的扰动.

为提升机动飞行下执行器的控制精度, 现有研究大致可分为基于模型与基于测量两类. 基于模型的方法致力于建立旋翼高保真模型:Bauersfeld等[3]将叶素理论旋翼模型与神经网络相结合, 以叶素理论刻画高速入流下的升力变化, 以数据驱动神经网络学习剩余力与力矩残差;Liu 等 [4] 通过全包线风洞试验辨识推进模型, 并将局部雅可比矩阵用于增量非线性动态逆 (INDI) 控制, 在机动飞行中在线计算局部升力变化所需的控制量, 以提高大机动条件下的控制分配精度. 此类方法精度较高, 但普遍依赖大量试验数据的训练或辨识.

基于测量的方法则通过力传感器直接感知旋翼升力并进行控制:Gonzalez-Morgado 等 [5] 采用应变片式测力方式检测机臂形变, 间接测量旋翼升力并结合比例-积分-微分 (PID) 控制抑制地面效应与天花板效应, 但应变片测量会引入高频噪声、信噪比较低;Jiang 等 [6,7] 在机臂与旋翼连接处加装力传感器直接测量升力, 并针对旋翼动力系统的非线性设计升力反馈线性化控制器, 通过单自由度台架实验验证了其在风扰环境下提高姿态控制精度的能力. 上述工作证明了升力闭环控制的有效性, 但均针对悬停或近悬停工况, 尚未覆盖高机动飞行下动态斜来流的作用.

在旋翼气动建模方面, 叶素理论在高风速下能够较精确地刻画单个旋翼的升力特性, 已形成较为成熟的建模方案.Theys 等 [8] 针对 $0 ^ { \circ } - 9 0 ^ { \circ }$ 桨盘攻角开展风洞实验, 比较了叶素动量理论与涡格法的预测能力;Serrano 等 [9] 进一步评估了非零攻角条件下多种诱导入流模型的精度;Simmons 等 [10] 利用全攻角风洞数据辨识了包含电机静、动态特性与螺旋桨气动特性的推进系统模型. 上述工作为建立旋翼动态入流模型奠定了理论基础, 但均处于风洞稳态来流条件, 难以复现旋翼运动与加速过程中的动态入流特征.

综上所述, 高保真辨识模型依赖大量专用试验数据且泛化性有限, 现有升力反馈控制亦多在悬停工况下验证, 其在高机动动态来流下补偿模型失配的能力尚不明确; 叶素理论模型虽能刻画稳态斜来流下的升力特性, 却缺乏对旋翼运动与加速过程的动态入流描述. 因此, 亟需一种能够复现高机动工况、且无需大规模试验辨识的旋翼建模与升力反馈控制方法.

针对上述问题, 本文的主要贡献如下: 1) 以变桨盘攻角的叶素理论模型为基础, 建立考虑无人机机动飞行状态的单旋翼升力机理模型, 并将影响轴向升力的变量归约为由轴向与面内来流、来流方位角、桨盘面内角速度与转速所构成的低维集合; 2) 提出以无需升力试验数据修正升力预测值的机理模型为前馈、以直接升力测量值为反馈的旋翼升力复合控制架构, 并将其部署于实际飞控; 3) 搭建桨盘攻角与来流速度可调的旋转式单旋翼测试台, 复现高机动飞行中的来流工况, 并在其上验证所提模型与控制架构的有效性.

全文结构如下: 第 1 节对无人机机动飞行时的旋翼运动状态进行建模; 第 2 节分析传统控制架构的局限并建立旋翼升力闭环控制架构; 第 3 节介绍桨叶几何与翼型气动数据获取、旋转测试台搭建及飞控部署等实现细节; 第 4 节在旋转测试台上验证旋翼模型精度与升力闭环控制效果; 第 5 节总结全

文.

## 1 机动飞行状态下的旋翼建模

## 1.1 坐标系与符号约定

简化的四旋翼无人机模型如图 1 所示. 定义机体坐标系 $\boldsymbol { B } = \{ O _ { b } ; \boldsymbol { x } _ { b } , \boldsymbol { y } _ { b } , z _ { b } \}$ 为前–右–下坐标系, 原点位于机体质心; 定义惯性坐标系 $\mathcal { L } =$ $\{ O _ { e } ; x _ { e } , y _ { e } , z _ { e } \}$ 为北–东–地坐标系. 记 $\pmb { R } = \pmb { R } ( \pmb { q } ) \in$ $S O ( 3 )$ 为由 B 至 I 的旋转矩阵, 无人机的运动状态由位置 $\pmb { p } \in \mathbb { R } ^ { 3 }$ 、速度 $\pmb { v } \in \mathbb { R } ^ { 3 }$ 、姿态四元数 q 与机体角速度 $\boldsymbol { \omega } = [ \omega _ { x } , \ \omega _ { y } , \ \omega _ { z } ] ^ { \mathrm { T } }$ 描述, 满足

$$
\dot {\boldsymbol {p}} = \boldsymbol {v}, \qquad \dot {\boldsymbol {q}} = \frac {1}{2} \boldsymbol {q} \otimes \left[ \begin{array}{c} 0 \\ \omega \end{array} \right]\tag{1}
$$

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/fc6fda0a430c38f37c3e0c01efdf1286c952c3bfefe26360f09f2d04d2d8264a.jpg)



图 1 四旋翼模型与机体/惯性坐标系定义



Fig. 1 Quadrotor model and definition of body/inertial frames


设第 i 个旋翼 (i = 1,2,3,4) 的桨毂中心在机体系下的安装位置为常矢量 $\boldsymbol { r } _ { i } ~ \in ~ \mathbb { R } ^ { 3 }$ , 桨盘法向单位矢量取为升力正方向, 对于共面等桨距布局有 ${ \pmb n } _ { i } = [ 0 , \ 0 , \ - 1 ] ^ { \mathrm { T } }$ . 以 $\sigma _ { i } = \pm 1$ 表示旋翼转向,$\sigma _ { i } = + 1$ 表示旋翼角速度沿 $+ n _ { i }$ 方向; 以 $\Omega _ { i } > 0$ 表示旋翼转速, $\psi _ { i }$ 表示桨叶方位角 (在桨盘平面内自$\mathbf { \mathcal { x } } _ { b }$ 轴量起). 环境风速在惯性系下记为 ${ \pmb v } _ { w }$ 

## 1.2 桨毂运动学与相对来流分解

由于旋翼与机体固连, 在机体系下有 ${ \dot { \mathbf { r } } } _ { i } \equiv \mathbf { 0 }$ , 故第 i 个旋翼桨毂在惯性系下的位置、速度与加速度分别为

$$
\pmb {p} _ {i} = \pmb {p} + \pmb {R r} _ {i}\tag{2}
$$

$$
\boldsymbol {v} _ {i} = \boldsymbol {v} + \boldsymbol {R} (\boldsymbol {\omega} \times \boldsymbol {r} _ {i})\tag{3}
$$

$$
\boldsymbol {a} _ {i} = \boldsymbol {a} + \boldsymbol {R} [ \dot {\boldsymbol {\omega}} \times \boldsymbol {r} _ {i} + \boldsymbol {\omega} \times (\boldsymbol {\omega} \times \boldsymbol {r} _ {i}) ]\tag{4}
$$

式 (4) 中 ${ \dot { \mathbf { \mathcal { \omega } } } } _ { \mathbf { \mathcal { \omega } } } \sim \mathbf { \mathcal { r } } _ { i }$ 为机体角速度变化产生的 Euler 加速度; 当机体转轴方向固定时, 该项表现为绕转轴运动的切向加速度 $. { \boldsymbol { \omega } } \times \left( { \boldsymbol { \omega } } \times { \boldsymbol { r } } _ { i } \right)$ 为向心加速度, 其方向由桨毂指向机体瞬时转轴; 二者共同构成旋翼所承受的附加过载.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/3515da0090d07341ab53c68fa2a62063a8cfdeb93ebbfaad473f26e09005278c.jpg)


在明确桨毂自身的刚体运动之后, 进一步计入环境风的影响, 考察桨毂相对气流的运动状态. 计入环境风后, 桨毂中心相对于空气的速度在机体系下表示为

$$
\boldsymbol {u} _ {i} = \boldsymbol {R} ^ {\mathrm{T}} (\boldsymbol {v} - \boldsymbol {v} _ {w}) + \boldsymbol {\omega} \times \boldsymbol {r} _ {i}\tag{5}
$$

将 $\mathbf { \Delta } \mathbf { u } _ { i }$ 沿桨盘法向与桨盘平面内分解, 得到轴向来流速度与面内 (侧向) 来流速度

$$
V _ {a, i} = \boldsymbol {u} _ {i} ^ {\mathrm{T}} \boldsymbol {n} _ {i}, \qquad V _ {t, i} = \left\| \left(\boldsymbol {I} _ {3} - \boldsymbol {n} _ {i} \boldsymbol {n} _ {i} ^ {\mathrm{T}}\right) \boldsymbol {u} _ {i} \right\|\tag{6}
$$

其中 $V _ { a , i }$ 以爬升方向为正. 相应地, 来流倾角(即来流方向与桨盘法向的夹角) 与来流方位角定义为

$$
\begin{array}{r} \alpha_ {p, i} = \mathrm{atan2} (V _ {t, i}, V _ {a, i}), \\ \psi_ {w, i} = \mathrm{atan2} (u _ {i, y}, u _ {i, x}) \end{array}\tag{7}
$$

设桨半径为 $R _ { p } ,$ 定义前进比与轴向入流比

$$
\mu_ {i} = \frac {V _ {t , i}}{\Omega_ {i} R _ {p}}, \qquad \lambda_ {c, i} = \frac {V _ {a , i}}{\Omega_ {i} R _ {p}}\tag{8}
$$

诱导入流比 $\lambda _ { \mathrm { i n d } , i }$ 由 Glauert 前飞动量定理 [11]确定, 尾迹偏斜角为 χ<sub>i</sub>:

$$
\begin{array}{r} \lambda_ {\mathrm{ind}, i} = \lambda_ {c, i} + \frac {C _ {T}}{2 \sqrt {\mu_ {i} ^ {2} + \lambda_ {\mathrm{ind} , i} ^ {2}}}, \\ \chi_ {i} = \arctan \frac {\mu_ {i}}{\lambda_ {c , i} + \lambda_ {\mathrm{ind} , i}} \end{array}\tag{9}
$$

式中 $C _ { T } = T _ { i } / \left( \rho _ { \infty } \pi R _ { p } ^ { 2 } ( \Omega _ { i } R _ { p } ) ^ { 2 } \right)$ 为基于桨尖速度的旋翼拉力系数, 其中 $T _ { i }$ 由第 1.3 节式 (17) 的叶素积分给出 $\ J _ { \infty }$ 为空气密度.


图 2 旋翼坐标、叶素离散及局部来流与气动力分解



Fig. 2 Rotor coordinates, blade element discretization and decomposition of local inflow and aerodynamic forces


## 1.3 叶素气动力建模

如图 2 所示, 对位于展向位置 $\rho \in [ \rho _ { 0 } , \ R _ { p } ]$ 、方位角 $\psi$ 处的叶素, 综合式 (5)∼ 式 (9), 其相对空气的切向速度与法向速度为

$$
U _ {T} (\rho , \psi) = \Omega_ {i} \rho + \sigma_ {i} V _ {t, i} \sin (\psi - \psi_ {w, i})\tag{10}
$$

$$
U _ {P} (\rho , \psi) = V _ {a, i} + v _ {\mathrm{ind}} (\rho , \psi)\tag{11}
$$

式 (10) 中的 $\sigma _ { i } V _ { t , i } \sin ( \psi - \psi _ { w , i } )$ 项反映了侧向来流造成的前行桨叶与后行桨叶的动压不对称; $v _ { \mathrm { i n d } } ( \rho , \psi )$ 为诱导入流速度.

由式 (10) 和式 (11) 可得叶素处的入流角与有效迎角

$$
\phi (\rho , \psi) = \arctan {\frac {U _ {P}}{U _ {T}}},\tag{12}
$$

$$
\alpha_ {\mathrm{eff}} (\rho , \psi) = \theta (\rho) - \phi (\rho , \psi)
$$

其中 $\theta ( \rho )$ 为由摄影测量获得的无载桨叶安装角

分布, 本文采用刚性桨叶近似.

式 (11) 中的诱导速度 $v _ { \mathrm { i n d } }$ 无法直接测量, 需要建模确定. 在轴向来流下, 诱导速度在桨盘内近似均$\hat { \simeq } 5$ ; 而在斜来流下, 尾迹发生偏斜, 诱导速度沿桨盘呈现前行–后行方向 (纵向) 的非均匀分布. 本文采用 Serrano 等验证的一阶谐波线性入流模型 [9], 将局部诱导入流比表示为平均诱导入流比与纵向一阶谐波之和:

$$
\begin{array}{r l} & v _ {\mathrm{ind}} (\rho , \psi) = \lambda_ {\mathrm{ind}} (\rho , \psi) \Omega_ {i} R _ {p}, \\ & \lambda_ {\mathrm{ind}} (\rho , \psi) = \lambda_ {\mathrm{ind}, i} \left[ 1 + k _ {x} \frac {\rho}{R _ {p}} \sin (\psi - \psi_ {w, i}) \right] \end{array}\tag{13}
$$

式中 $\lambda _ { \mathrm { i n d } , i }$ 为由式 (9) 隐式确定的平均诱导入流比, $k _ { x }$ 为纵向入流梯度系数, 其大小随尾迹偏斜角 $\chi _ { i }$ 增大而增大; 当来流趋于轴向 $( \mu _ { i } \to 0 )$ 时$k _ { x }  0 .$ 式 (13) 退化为均匀入流. 由于 $\lambda _ { \mathrm { i n d } , i }$ 依赖于旋翼拉力系数 $C _ { T }$ (本身即待求量), 式 (9)–式 (17)构成耦合系统, 需通过固定点迭代求解: 先给定静态环境下悬停时的 $C _ { T }$ 初值求解 $\lambda _ { \mathrm { i n d , \cdot } }$ <sub>i</sub> 与 $v _ { \mathrm { i n d } }$ , 再由叶素积分更新 $C _ { T }$ , 迭代至收敛.

在得到局部速度场与诱导速度后, 叶素气动力由二维翼型极线查表获得. 对展向位置 $\rho _ { \setminus }$ 、方位角 $\psi$ 处的叶素, 其局部合速度为 $V _ { R } = \sqrt { U _ { T } ^ { 2 } + U _ { P } ^ { 2 } }$ , 当地雷诺数为

$$
R e (\rho , \psi) = \frac {\rho_ {\infty} c (\rho) V _ {R}}{\mu_ {\infty}}\tag{14}
$$

其中 $c ( \rho )$ 为弦长分布, $\mu _ { \infty }$ 为动力粘度. 以有效迎角 $\alpha _ { \mathrm { e f f } }$ 与雷诺数 $R e$ 查取由 XFOIL[12] 计算的翼型极曲线 $C _ { l } ( \alpha _ { \mathrm { e f f } } , R e )$ $C _ { d } ( \alpha _ { \mathrm { e f f } } , R e )$ , 得叶素单位展长的升力与阻力

$$
\begin{array}{l} \mathrm{d} L = \frac {1}{2} \rho_ {\infty} V _ {R} ^ {2} C _ {l} c (\rho) \mathrm{d} \rho , \\ \mathrm{d} D = \frac {1}{2} \rho_ {\infty} V _ {R} ^ {2} C _ {d} c (\rho) \mathrm{d} \rho \end{array}\tag{15}
$$

将 dL、dD 投影至旋翼轴线方向, 得叶素对轴向升力的贡献

$$
\mathrm{d} T = \mathrm{d} L \cos \phi - \mathrm{d} D \sin \phi\tag{16}
$$

沿有效展向区间 $[ \rho _ { 0 } , \ R _ { p } ]$ 与完整方位角 [0, 2π]积分, 并计入桨叶片数 $N _ { b } ,$ , 即得旋翼的轴向升力

$$
T _ {i} = \frac {N _ {b}}{2 \pi} \int_ {0} ^ {2 \pi} \int_ {\rho_ {0}} ^ {R _ {p}} \mathrm{d} T \mathrm{d} \rho \mathrm{d} \psi\tag{17}
$$

综上, 当无人机运动时, 影响任一旋翼产生升力的变量可以归约为:

$$
\pmb {s} _ {i} ^ {\mathrm{aero}} = \{V _ {a, i}, V _ {t, i}, \psi_ {w, i}, \Omega_ {i} \}\tag{18}
$$

于是旋翼轴向升力可表示为 $T _ { i } ~ = ~ f ( s _ { i } ^ { \mathrm { a e r o } } )$ . 其中$V _ { a , i }$ , $V _ { t , i } , \ \psi _ { w , i }$ 共同描述来流速度和倾角, 而 $\Omega _ { i }$ 描述旋翼转速.

## 2 控制架构

## 2.1 传统控制架构及其局限性

四旋翼无人机飞行控制器由位置-速度外环、姿态-角速度内环与控制分配器组成. 外环根据位置 $\varXi$ 速度误差生成期望总升力 $T$ 与期望姿态 $\theta _ { d } .$ , 内环生成期望控制力矩 $\boldsymbol { M } = [ \tau _ { x } , \tau _ { y } , \tau _ { z } ] ^ { \mathrm { T } }$ ; 控制分配器进一步将期望总升力与力矩分解为各旋翼的目标升力$T _ { d , i }$ . 随后, 升力-控制量映射器将 $T _ { d . }$ 转换为归一化电机指令 $u _ { i } .$ , 再由电子调速器、电机与螺旋桨产生实际升力 $T _ { i }$ . 该结构如图 $\mathrm { 3 ( a ) }$ 所示.

如图 3(b) 所示, 在现有开源飞控系统中 [13], 升力-控制量映射器通常定义为如下的静态二次映射:

$$
T _ {d, i} = f _ {m a p} (u _ {i}) = c _ {a} u _ {i} ^ {2} + (1 - c _ {a}) u _ {i}\tag{19}
$$

其中, $, c _ { a } \in [ 0 , 1 ]$ 为无人机悬停时标定的固定参数, 用于描述旋翼升力与转速之间的近似平方关系. 在近悬停和缓慢姿态变化条件下, 式 (19) 能够满足常规控制需求; 当局部来流发生显著变化时, 相同控制量对应的实际升力将随工况改变, 导致期望升力与实际升力之间产生系统性偏差. 由于传统架构缺少旋翼升力反馈, 该偏差只能通过外层姿态或位置误差间接修正, 控制作用链路较长, 并可能在强扰动或快速机动时引起超调和振荡.

## 2.2 升力闭环控制架构

为使控制系统直接感知执行器层面的实际作用力, 本文在控制分配器之后增设独立的旋翼升力内环, 该内环由前馈控制器与反馈补偿器两部分组成,如图 $3 ( \mathrm { c } )$ 所示. 前馈控制器包含旋翼升力逆模型与转速-控制量映射器. 给定期望升力 $T _ { d , i }$ 后, 旋翼升力逆模型依据当前来流速度和来流倾角求解所需的前馈转速 $\Omega _ { \mathrm { d , i } } ,$ , 再经静态标定的转速-控制量映射转换为前馈控制量 $u _ { \mathrm { f f , i } }$ . 前馈量已涵盖高机动工况下的来流速度与桨盘姿态信息, 但电池压降、旋翼间气动干扰等未建模误差仍会造成升力偏差, 故引入反馈补偿器予以校正. 反馈补偿器以期望升力$T _ { d , i }$ 与同轴力传感器实测升力 $T _ { i }$ 之差为输入, 生成控制修正量 u , 与前馈控制量叠加得到总输出 $u _ { \mathrm { f b , i } } .$ $u _ { \mathrm { c , i } } = u _ { \mathrm { f f , i } } + u _ { \mathrm { f b , i } }$ 

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/a675648ab40d052f4b6c411994946d49be62c77e0119159e7a7fe106d3bb6a7f.jpg)



图 3 四旋翼无人机控制架构;(a) 总体控制架构;(b) 传统升力开环控制架构;(c) 升力闭环控制架构



Fig. 3 Control Architecture for Quadcopter UAVs; (a) Overall Control Architecture; (b) Conventional Open-Loop thrust Control Architecture; (c) Closed-Loop thrust Control Architecture


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/074a019c22ea7afc5868d08716bfe80acad1aeff63f07944ae43e63016bb317a.jpg)



(a)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/802f5f9d33863daf0229eaca2ef7fc34c9995fb297280e921a240917fca31353.jpg)



(b)



图 4 螺旋桨摄影测量、三维重建与截面提取过程;(a) 螺旋桨三维重建;(b) 截面提取



Fig. 4 Photogrammetry, 3D reconstruction and cross-section extraction of the propeller;(a)3D reconstruction of the propeller;(b)Cross-section extraction


## 3 实施

本节介绍上述理论方法从理论到实现的完整工程链条。首先为了离线完整计算叶素理论, 通过摄影测量提取桨叶几何与翼型气动数据; 随后搭建了模拟高机动飞行工况的旋转式单旋翼测试台, 并介绍了升力测量单元的结构细节和传感器标定方法; 最后将升力闭环控制架构部署于实际飞控, 并介绍了转速-控制量静态标定方法. 在实施过程中, 部署于飞控的升力模型前馈无需升力试验数据进行修正,只需要摄影测量得到的桨叶几何参数, 以及静态标定转速-控制量映射即可.

## 3.1 桨叶几何与翼型气动数据获取

叶素模型需要两类输入: 一类是弦长 $c ( \rho )$ 、安装角 $\theta ( \rho )$ 及翼型轮廓随径向位置的变化, 另一类是各截面在有效迎角 $\alpha _ { \mathrm { e f f } }$ 和雷诺数 $R e$ 下的二维气动系数 $C _ { l } , \ C _ { d } . \mathrm { U I U C }$ 等公开数据库能够提供部分通用翼型坐标 [14], 但商业螺旋桨通常只标注直径和标称桨距, 缺少上述径向几何及截面数据 [15]. 为此, 本文按照摄影测量重建、径向截面提取、二维极线计算的流程获取 $\mathrm { T } \mathrm { - } \mathrm { M o t o r } \ \mathrm { P 1 8 } { \times } 6 . 1 \mathrm { C F }$ 螺旋桨的模型输入.

三维重建能够将实物的几何信息数字化, 其关键在于获取具有稳定尺度和充分表面特征的稠密点云. 常用方法可分为激光扫描和摄影测量两类 [16]:前者精度较高, 但设备成本高昂; 后者仅需普通相机即可有效控制成本, 但对光照条件较为敏感——物体表面的镜面反光及低纹理区域易导致特征匹配失败、点云产生空洞或局部几何畸变 [17]. 为消除光照的干扰, 现有应用通常需要将待重建物体置于背景洁净、光照均匀且无镜面反射的实验室环境中拍摄,这在一定程度上限制了摄影测量在现场或非受控场景下的适用性.

针对碳纤维桨叶表面光泽度高、易产生镜面反光这一特点, 本文在拍摄前于桨叶表面均匀撒布一层薄层玉米淀粉, 利用其亚光、微粒特性抑制碳纤维表面的镜面反光并引入随机纹理, 从源头上降低了摄影测量对光照条件的敏感性. 由此, 本文无需专业光源和暗室实验室环境, 在光照不受控的普通室内环境下完成 $\vec { \mathsf { J } }$ 螺旋桨的高质量建模. 具体地, 本文从上、中、下三个高度环绕拍摄, 相邻方位的角度间隔不超过 $1 0 ^ { \circ }$ , 同时补充不同俯仰角下的图像, 以保证桨叶各处表面特征均被充分覆盖. 照片导入 $\mathrm { R e } { } \cdot$ alityScan 后依次完成特征匹配、稠密点云重建和三角网格生成. 以桨毂中心为坐标原点, 利用实测桨径校准模型尺度, 并将模型 z 轴与螺旋桨旋转轴对齐,得到可按无量纲径向位置 $r / R$ 索引的桨叶网格. 图$4 ( \mathrm { a } )$ 给出了重建点云及相机位姿, 图 4(b) 给出了对齐后的桨叶模型.

三维网格本身不能直接作为叶素模型输入, 还需转换为沿展向排列的二维截面. 在给定 $r / R$ 处,以同轴圆柱面与桨叶网格求交, 将交线展开并投影到局部二维坐标系; 识别前、后缘后, 分别对上、下表面进行平滑拟合, 以减弱点云噪声及网格在尖锐边缘处的畸变. 由拟合轮廓计算弦长 $c ( \rho )$ 、安装角$\theta ( \rho )$ 和相对厚度 $t / c ,$ 再以弦长归一化截面坐标.

摄影测量得到的是无载外形, 载荷引起的弹性扭转会改变有效安装角, 弯曲会改变局部截面姿态与入流关系, 从而影响有效迎角和升力预测. 然而弹性变形需要沿桨叶展向的等效弯曲刚度、扭转刚度等结构参数; 为简化离线建模流程, 本文采用刚性桨叶近似, 暂未计入载荷引起的几何变化.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/e34715704f0962a176fa136adf3eb4bd9c2f287750e4da0c668398f87658967d.jpg)



图 5 桨叶弦长比与安装角的径向分布 $( 0 . 2 5 \leq r / R \leq 0 . 9 0 )$ Fig. 5 Radial distributions of blade chord ratio and pitchangle $( 0 . 2 5 \leq r / R \leq 0 . 9 0 )$


为检验几何提取结果, 将弦长比 $c / R$ 和安装角θ 的径向分布与 Carroll[18] 基于激光扫描获得的 T-$\mathrm { M o t o r ~ 1 8 { \times } 6 . 1 }$ 桨叶数据进行比较, 如图 5 所示. 选取 $0 . 2 5 \leq r / R \leq 0 . 9 0$ 的主要气动承载区间作为比较区间, 将两组曲线插值至同一径向网格, 并以两者均值作为相对差异的归一化基准. 弦长比的平均绝对差异、均方根差异和最大绝对差异分别为 0.010、0.011 和 0.018, 平均相对差异为 6.0%; 安装角的上述三项绝对差异分别为 0.54<sup>◦</sup>、0.60<sup>◦</sup> 和 1.25<sup>◦</sup>, 平均相对差异为 4.8%. 两项参数的曲线相关系数均约为0.995, 表明摄影测量能够准确描述桨叶的弦长与安装角变化, 其几何分辨率满足本文叶素模型的输入要求.

最后, 将各径向位置的归一化截面坐标输入XFOIL[12], 在覆盖本文叶素工作范围的 $\alpha _ { \mathrm { e f f } }$ –Re 离散网格上计算二维极线, 建立供第 1.3 节查取的$C _ { l } ( \alpha _ { \mathrm { e f f } } , R e )$ 和 $C _ { d } ( \alpha _ { \mathrm { e f f } } , R e )$ 数据库.

## 3.2 高机动工况构造: 旋翼测试台

为在地面条件下构造可重复的高机动工况, 本文搭建旋转悬臂式单旋翼测试平台, 如图 $6 ( \mathrm { a } )$ 所示.驱动电机带动转盘和悬臂绕竖直轴旋转, 旋翼单元安装于距离旋转中心 $R _ { 0 }$ 的悬臂末端上. 旋翼单元的细节如图 $6 ( \mathrm { b } )$ 所示, 通过倾转支架与竖直方向的夹角 $\theta ,$ 进而调节桨盘攻角 $\alpha _ { p } ;$ 通过转台角速度 $\Omega _ { a }$ 改变旋翼单元面对的来流速度.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/d4ee5e3cbc9d6d1f7ed0719d5133eda852b5b2f754017073df588b3027d3f512.jpg)



(a)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/cbe127cd3b26662d8de65b20f4d19872c34ed51538b7e3fa330071dd37295f4d.jpg)



(b)



图 6 旋转悬臂式单旋翼测试平台;(a) 整体结构;(b) 旋翼单元



Fig. 6 Rotating cantilevered single-rotor test platform; (a) overall structure; (b) rotor unit


当 $\alpha _ { p } \neq 0$ 时, 旋翼单元中心的相对来流同时具有垂直于桨盘的轴向分量 $V _ { a , i }$ 和位于桨盘内的切向分量 $V _ { t , i }$ :

$$
V _ {a, i} = \Omega_ {a} R _ {0} \cos \alpha_ {p}, \qquad V _ {t, i} = \Omega_ {a} R _ {0} \sin \alpha_ {p}\tag{20}
$$

代入式 (8) 即可得到测试台工况下的前进比 $\mu _ { i }$ 与轴向入流比 $\lambda _ { c , i } ,$ 进而由式 (9) 确定平均诱导入流比$\lambda _ { \mathrm { i n d } , i } .$ 

桨叶坐标遵循图 2 定义, 对位于 $( \rho , \psi )$ 处的叶素, 局部轴向速度 $U _ { P }$ 和切向速度 $U _ { T }$ 表示为:

$$
\begin{array}{r} U _ {P} (\rho , \psi) = \Omega_ {a} (R _ {0} - \rho \cos \psi) \cos \alpha_ {p} + v _ {\mathrm{ind}} (\rho , \psi) \\ U _ {T} (\rho , \psi) = \Omega_ {a} \rho - \Omega_ {a} (R _ {0} - \rho \cos \psi) \sin \alpha_ {p} \cos \psi \end{array}\tag{21}
$$

式中 $\mathrm { , } v _ { \mathrm { i n d } } ( \rho , \psi )$ 为诱导速度, 由式 (13) 确定. 由式 (12) 可得入流角 $\phi$ 和叶素有效迎角 $\alpha _ { \mathrm { e f f } }$ 

旋翼测试台基本参数如表 1 所示, 测试台能构造的最大来流速度为 10.2m/s, 根据 $\tau = J \dot { \omega }$ , 带负载能达到的最大角加速度 ω˙ 为 $7 . 3 8 \mathrm { r a d / s ^ { 2 } }$ , 旋翼单元受到指向旋转轴的向心过载最大为 $7 . 1 \mathrm { g } ,$ 受到的面向来流的过载最大为 1.1g.

现有关于高机动飞行的研究中 [4,19,20] 最大速度的量级在 $5 { \mathrm { - } } 1 2 . 9 { \mathrm { m } } / { \mathrm { s } } ,$ 沿总升力方向的过载量级在$1 . 6 3 \mathrm { - } 2 . 2 \mathrm { g } .$ . 本文搭建的测试台能基本涵盖上述指标,因此能在式 (18) 的变量层面和式 (4) 的加速度层面构造高机动飞行下的动态来流.


表 1 旋翼测试台参数



Table 1 Rotor test bench parameters


<table><tr><td>参数</td><td>值</td></tr><tr><td>总转动惯量 J</td><td>9.42 kg·m2</td></tr><tr><td>悬臂长度 R0</td><td>1.5 m</td></tr><tr><td>最大转速 Ωa,max</td><td>64.9 rpm</td></tr><tr><td>最大扭矩 τ</td><td>69.5 N·m</td></tr></table>


算法 1 离线升力查找表生成



Algorithm 1 Ofline generation of the thrust lookup table


Require: 桨叶几何与翼型极线; 工况网格 $\{\alpha_{p}, V_{\infty}, \Omega\}$ Ensure: 升力表 $T(\alpha_{p}, V_{\infty}, \Omega)$ 1: for 每个 $(\alpha_{p}, V_{\infty})$ do
2: $V_{a}, V_{t}, \psi_{w} \leftarrow V_{\infty} / \alpha_{p}$ 3: for 每个 $\Omega$ do
4: 初始化诱导入流比 $\lambda_{\mathrm{ind}}$ 5: repeat
6: 由式 (21) 计算局部来流速度
7: 按式 (15)-(16) 积分叶素升力 $T$ 8: 按式 (9) 阻尼更新 $\lambda_{\mathrm{ind}}$ 9: until $\lambda_{\mathrm{ind}}$ 收敛或达到迭代上限
10: 存储 $T(\alpha_{p}, V_{\infty}, \Omega)$ 11: end for
12: 校验 $T$ 沿 $\Omega$ 方向单调递增
13: end for

## 3.3 飞控部署

上述推导的完整叶素动量理论模型, 计算量庞大, 难以在机载控制器上实时求解. 因此本文采用全工况离线求解、在线查表的部署方式:

1. 离线阶段在 $( \alpha _ { p } , V _ { \infty } , \Omega )$ 网格上求解正向升力模型并生成查找表, 流程如算法 1 所示;

2. 在线阶段依据期望升力与实时工况量反查所需转速 (见算法 2).

3. 在线查表给出期望升力到转速的前馈逆映射, 而转速还需进一步转换为归一化电机控制量. 在实际测试中, $\mathrm { , 0 { - } 1 0 m / s }$ 左右的来流下, 转速-控制量之间的关系基本恒定, 影响升力的是实际升力与转速之间的关系. 为使前馈项的转速输出能够发挥作用,需要先标定转速-控制量之间的静态映射关系: 在固定台架上选择 0-100% 油门之间的 13 个固定点位,读取对应的电机控制量和实际转速, 拟合得到

$$
u _ {\mathrm{ff}} = a \Omega^ {2} + b \Omega + c\tag{22}
$$

其中,Ω 为电机转速 $, a , b , c$ 为拟合出的常系数.

4. 反馈补偿器选用 PID 控制器, 其结构简单、计算量小, 能够以较高频率运行以快速抑制模型残差与外部扰动.

算法 2 在线升力逆查表

Algorithm 2 Online inverse lookup of the thrust tableRequire: $T _ { c } \setminus \Omega _ { a } \setminus \alpha _ { p } \setminus R _ { 0 } ;$ 离线升力表 $_ T$ Ensure: 前馈转速 $\Omega _ { \mathrm { f f } }$ 1: $V _ { \infty } \gets \Omega _ { a } R _ { 0 }$ 2: 将 $( \alpha _ { p } , V _ { \infty } )$ 限制在表内并双线性插值得 $T ( \Omega _ { k } )$ 3: T∗ ← clip(T<sub>c</sub> $, T ( \Omega _ { 0 } ) , T ( \Omega _ { K - 1 } ) \big )$ 4: 沿 Ω 方向反插 $\Omega _ { \mathrm { f f } }  T ^ { - 1 } ( T _ { c } ^ { * } )$ 5: return $\Omega _ { \mathrm { f f } }$ 

## 3.4 力传感器集成

直接升力反馈要求传感器能够在不改变主要传力路径的条件下测量旋翼轴向作用力. 应变片机臂测力方案易受结构模态、温漂与装配差异影响, 而专用力传感器能够提供更直接的载荷观测 [6,13]. 本文采用 SBT673 小型拉压力传感器, 额定量程为 10kg,对应额定轴向力为 98.07N, 标称精度为 0.1%.

如图 6(b) 所示, 测量组件自上而下依次由螺旋桨、电机、连接板、力传感器组成. 螺旋桨产生的轴向升力经电机与连接板传递至传感器受力端. 传感器信号经零偏校准、比例换算和低通滤波后得到升力测量值 $T _ { i }$ .

所述零偏校准, 主要用于补偿传感器安装载荷在轴向和径向过载工况下产生的测量误差. 具体而言，当旋翼电机无转速时，在旋转测试台上，进行不同加速时间 (测试台从静止到最大转速的时间) 的动态测试，补偿后的输出模型为:

$$
T _ {i} = T _ {i} - A a _ {z} - B a _ {x}\tag{23}
$$

其中 $T _ { i }$ 为传感器测量值, 单位为 $\mathrm { N } ; A { = } 0 . 3 6 1$ $B { = } 0 . 0 3 3$ , 分别为传感器轴向和径向载荷的补偿系数, 与传感器安装的载荷质量与安装误差有关, 单位为 kg; ${ ; a _ { z } }$ 和 $a _ { x }$ 分别为沿传感器轴向和径向的加速度值, 通过测试台悬臂末端安装的飞控加速度计获取,并投影到传感器轴向和径向, 单位为 $\mathrm { m } / \mathrm { s } ^ { 2 }$ . 补偿前后的传感器测量数据如图 7 所示.

## 4 结果

为验证所提出的旋翼升力模型与升力闭环控制器, 本文在旋转测试台上开展两类实验: 其一, 执行如表 2 所示的工况测试, 将第 1 节叶素动量模型的预测升力与实测升力对比, 验证模型精度; 其二, 按传统升力开环控制、纯升力反馈、模型前馈与升力反馈复合控制三级对照方案, 验证所提出的升力反馈和前馈-反馈复合控制方案的控制效果.

## 4.1 旋翼升力模型精度验证

测试对象为 T-Motor MN5008 KV340 电机与P18×6.1CF 螺旋桨, 旋翼轴向升力由同轴力传感器测量, 转台角速度由安装在悬臂末端的飞控惯性测量单元 (IMU) 记录, 电机转速由 AS5600 磁编码器获取. 试验选取约 3000、4000 和 $5 0 0 0 \mathrm { r p m }$ 的典型转速, 在每个工况点停留 3s, 记录对应的旋翼转速和升力, 具体实验设置如表 2 所示.


表 2 旋翼测试台测试设置



Table 2 Test settings of the rotor test bench


<table><tr><td>转速档位</td><td>攻角</td><td>来流速度</td></tr><tr><td>3000 rpm</td><td></td><td></td></tr><tr><td>4000 rpm</td><td>0-90°(间隔 15°)</td><td>0-10.2 m/s(间隔 10%)</td></tr><tr><td>5000 rpm</td><td></td><td></td></tr></table>

3 组转速档位、7 种不同攻角、11 个来流速度, 共231 个分档工况点, 每个工况点以式 (8) 定义的螺旋桨前进比表示. 以式 (9) 定义的升力系数 $C _ { T }$ 作为精度衡量指标. 定义残差为 $\delta C _ { T } = C _ { T , \mathrm { e x p } } - C _ { T , \mathrm { t h e o r y } } ,$ 相对残差定义为 $\varepsilon _ { T } = \delta C _ { T } / C _ { T , \mathrm { t h e o r y } } \times 1 0 0 \%$ 


(a)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/0b860ae4c34c647696259db6692c3aad7ebb264e92e30511701d597a5dfc0073.jpg)



(b)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/708d1bf2f192c30c12dafba211b1fc1a12ab335acf4bf653c548aac98a040e06.jpg)



图 7 升力系数一致性与攻角分区残差分布



Fig. 7 Thrust coeficient agreement and residual distributions by disk angle of attack


图 7(a) 给出了 231 个分档工况点上理论值与实验值的一致性. 全部点的 Pearson 相关系数为 0.960, 线性回归为 $C _ { T , \mathrm { { e x p } } } ~ = ~ 0 . 8 6 1 C _ { T , \mathrm { { t h e o r y } } } ~ +$ 0.0013, 回 归 决 定 系 数 $R ^ { 2 } = 0 . 9 2 2 ,$ 一致性相关系数 CCC 为 0.954. 其中 $, 4 4 . 6 \% ( 1 0 3 / 2 3 1 )$ 的点满足 $\delta C _ { T } ~ < ~ 0 . 6 4 . 1 \% ( 1 4 8 / 2 3 1 )$ 满足 $| \delta C _ { T } | \ \leq$ $0 . 0 0 0 5 , 8 9 . 6 \% ( 2 0 7 / 2 3 1 )$ 满足 $| \delta C _ { T } | \ \leq \ 0 . 0 0 1$ . 以$C _ { T } = 0 . 0 0 2$ 和 0.014 为量级参照,0.0005 分别相当于25.0% 和约 3.6% 的相对偏差, 因此固定绝对阈值不能视为统一的相对精度. 按各点理论值归一化后, 这231 点的 $\left| \varepsilon _ { T } \right|$ 中位数为 3.72%.

图 7(b) 进一步给出攻角分区结果 $. \alpha _ { p } = 0 ^ { \circ }$ 和$4 5 ^ { \circ }$ 的残差中位数分别为 $0 . 5 3 2 \times 1 0 ^ { - 3 }$ 和 $0 . 5 2 8 \times$ $1 0 ^ { - 3 }$ ,以理论低估为主; $\mathrm { 1 5 ^ { \circ } \cdot 3 0 ^ { \circ } }$ 和 $6 0 ^ { \circ }$ 的中位数分别为 $- 0 . 0 9 8 \times 1 0 ^ { - 3 } , 0 . 0 9 0 \times 1 0 ^ { - 3 }$ 和 $0 . 1 7 4 \times 1 0 ^ { - 3 } . 7 5 ^ { \circ }$ 和90<sup>◦</sup> 的中位数转为 $- 0 . 4 3 6 \times 1 0 ^ { - 3 }$ 和 $- 0 . 8 0 7 \times 1 0 ^ { - 3 }$ ,负残差点分别占 $8 7 . 9 \% ( 2 9 / 3 3 )$ 和 $9 0 . 9 \% ( 3 0 / 3 3 ) . 9 0 ^ { \circ }$ 组的四分位距为 $1 . 1 3 1 \times 1 0 ^ { - 3 }$ , 大于 $7 5 ^ { \circ }$ 组的 0.278×$1 0 ^ { - 3 }$ , 显示该分区的理论高估更明显且残差分布更宽. 因此, 偏差方向随攻角呈非单调变化, 总体负残差比例不能代表各分区均无系统偏差. 上述结果是三个转速档位合并后的工况间描述性比较, 不构成独立重复试验的显著性检验.


表 3 不同桨盘攻角下的旋翼升力模型误差统计



Table 3 Error statistics of the rotor thrust model at diferent disk angles of attack


<table><tr><td><eq>\alpha_p/(^\circ)</eq></td><td><eq>RMSE_{norm}/\%</eq></td><td><eq>MaxErr_{norm}/\%</eq></td><td>MAPE/%</td></tr><tr><td>0</td><td>7.43</td><td>12.67</td><td>8.93</td></tr><tr><td>15</td><td>3.91</td><td>14.94</td><td>4.70</td></tr><tr><td>30</td><td>3.26</td><td>9.65</td><td>3.97</td></tr><tr><td>45</td><td>5.02</td><td>9.73</td><td>5.33</td></tr><tr><td>60</td><td>2.46</td><td>6.92</td><td>2.17</td></tr><tr><td>75</td><td>4.42</td><td>11.74</td><td>3.63</td></tr><tr><td>90</td><td>10.04</td><td>19.75</td><td>7.02</td></tr><tr><td>全部</td><td>5.76</td><td>19.75</td><td>5.08</td></tr></table>

表 3 汇总了按桨盘攻角合并三个转速后理论$C _ { T }$ 值与实际 $C _ { T }$ 值的误差. 全部样本的归一化均方根误差 (RMSE) 为 5.76%, 平均绝对百分比误差(MAPE) 为 5.08%. 在 $1 5 ^ { \circ } - 7 5 ^ { \circ }$ 斜来流范围内, 按攻角汇总的 RMSE 为 $2 . 4 6 \% - 5 . 0 2 \% ;$ 两个端点工况的误差相对较大:0<sup>◦</sup> 和 $9 0 ^ { \circ }$ 的汇总 RMSE 分别为7.43% 和 10.04%.

其他关于叶素动量理论 (BEMT) 旋翼建模的研究中, 误差量级为:Carroll[18] 等使用激光扫描提取桨叶翼型和气动参数, 建立了与本文一致的 Tmo-$\mathrm { t o r P 1 8 } { \times } 6 . 1$ 螺旋桨的变攻角 BEMT 模型, 其理论与试验结果的误差范围为 5% − 15%;Serrano 等 [9] 表明, 引入 Glauert 或 Coleman 非均匀入流模型后, 非零攻角下的最大偏差可控制在 15% 以内;Theys 等[8] 则指出, 传统 BEMT 和涡格法虽能预测斜流下的总体趋势, 但精度会随来流倾斜显著下降, 在小角度下误差量级约为 10%, 在大角度斜流下误差量级约 10% − 30%. 相比之下, 本文模型在各攻角下的RMSE 小于 10%, 在所有工况点下的最大误差小于20%, 与现有研究中的物理模型处于同一量级, 进一步验证了 3.1节中摄影测量的精度和旋翼叶素模型的准确性. 该精度能够为后续模型前馈提供有效基准, 其余模型失配则由升力反馈进一步补偿.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/b9450f40ae781f5834e13881fd29a5adbf78c352e8e85d75fb06c3e57caafbfb.jpg)



图 8 来流速度曲线



Fig. 8 Freestream-speed curve


## 4.2 升力闭环控制效果验证

本节以 0<sup>◦</sup> 攻角下的纯轴向来流作为控制验证工况: 该工况下来流方向垂直于桨盘平面、轴向分量最大, 对旋翼升力的扰动最直接, 因此适合用于检验控制器对显著气动扰动的抑制能力. 进行三级对照实验:

1. 固定控制量方案按式 (19) 根据零来流静态标定关系给定与期望升力对应的控制量, 来流变化期间不作调整;

2. 纯反馈方案关闭第 2.2 节所述的旋翼升力模型前馈, 仅由升力误差生成反馈修正量 $u _ { \mathrm { f b } } ;$ 

3. 模型前馈与反馈复合控制依据转台角速度$\Omega _ { a }$ 与桨盘攻角 $\alpha _ { p }$ 估计的来流状态, 由旋翼升力逆模型给出期望转速 $\Omega _ { \mathrm { f f } }$ 与前馈控制量 $u _ { \mathrm { f f } } .$ , 反馈环仅补偿模型误差与未建模扰动.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/f117f89361ef1dcd183cbf9f663f16df0b8c5e1e29ef9829971bd164ffa1d132.jpg)



图 9 15、20、25 N 期望升力和 1 s 来流加速工况下三种控制方法的动态响应.(a)–(c) 分别为 15、20、25 N 期望升力下的实测升力与跟踪误差.



Fig. 9 Dynamic response of the three control methods under 15, 20, and 25 N desired thrust with the 1 s freestream-acceleration condition. (a)–(c) show the measured thrust and tracking error under 15, 20, and 25 N desired thrust, respectively.


其中, 纯升力反馈方案与模型前馈与反馈复合控制方案采用相同的 PID 参数, 复合控制中前馈项和反馈项的比例为 1 : 1. 试验覆盖期望升力 15、20、25 N 与来流加速时间 1、5、10 s(测试台从静止到最大速度的时间), 共构成 9 个匹配工况, 三种方法在同一工况下采用相同的目标升力阶跃指令、限幅与

数据处理流程.

来流速度 $V _ { \infty } = \Omega _ { a } R _ { 0 } ,$ , 各试验依据中值滤波后的 $V _ { \infty }$ 进行时间对齐. 对 1、5、10 s 全部工况采用同一评价规则: 以低、高平台速度差的 10% 和 90%阈值对应时刻分别记为 $t _ { 1 0 }$ 和 $t _ { 9 0 }$ , 令 $\tau = t - t _ { 1 0 }$ , 扰动评价窗口统一取 $[ t _ { 1 0 } , t _ { 9 0 } + 3 \mathrm { s } ]$ , 即 10%–90% 加速段及其后 3 s. 采用相同的相对阈值可减小启停过渡与平台测量波动对边界确定的影响, 并统一包含加速后的恢复过程. 图 8 给出 1 s 来流加速工况下的来流速度曲线; 图 9、图 10 均采用上述时间对齐规则.

在该窗口内, 以期望升力 $T _ { c }$ 为统一归一化基准,定义方法 m 的升力跟踪误差指标为

$$
\begin{aligned} E_{m} & = \sqrt{\frac{1}{N_{m}}\sum_{k = 1}^{N_{m}}[T_{c} - T_{m}(t_{k})]^{2}},\\ \mathrm{NRMSE}_{m} & = \frac{E_{m}}{T_{c}}\times 100\% , \end{aligned}
$$

其中 $, T _ { m } ( t _ { k } )$ 为窗口内的实测升力, $, N _ { m }$ 为样本数, ${ \mathbf { } } , E _ { m }$ 的单位为 N. 表 4 报告无量纲的 NRMSE 百分数, 不以窗口内平均实测升力归一化, 也不扣除扰动前的升力偏置. 同一方法–工况存在重复试验时,先逐次计算指标再取算术平均. 两项降幅分别按$( 1 - E _ { \mathrm { F B } } / E _ { \mathrm { s t a t i c } } ) { \times } 1 0 0 \%$ 与 $( 1 - E _ { \mathrm { F F + F B } } / E _ { \mathrm { F B } } ) { \times } 1 0 0 \%$ 计算, 均使用未舍入数值.

图 9 给出 15、20、25 N 三个期望升力在 1 s 来流加速工况下的动态响应过程, 该工况下加速时间最短、来流变化最快, 最能体现瞬态控制差异. 与图8 中坐标轴定义一致, 竖虚线表示来流速度达到变化幅值 10% 的时刻, 浅灰色纵向区域为 10%–90% 加速段, 水平灰色区域表示期望升力的 ±5% 误差带.从图中可以看出, 三种期望升力的变化规律一致: 固定控制量下, 升力随轴向来流增加而大幅下降, 且加速结束后仍存在稳态偏差; 纯反馈能够逐步恢复升力, 但存在明显的瞬态跌落; 模型前馈与反馈复合控制在来流加速阶段即同步提高控制量, 将跟踪误差限制在更小范围内. 进一步绘制在 1s、5s、10s 三种来流加速时间下, 期望升力 20N 的动态响应过程, 如图 10 所示.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/561a2b6adaf918c24292823ca9f1207d95ed189c3c0ef6baa5f603aeca3de828.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/5707b5889809600ea8e7477d66451943b9931bd631c3686df3d25a870b5d896b.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/e6e7f88243106ea689206e2ee07c2ffd55febc54da857fd91939ebb5833acb01.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/0bf2de4ac1eb96b5b9ad1f12e6eb6d9222ecf8f4e99120d4d1b408a85e66c069.jpg)



时间 (s)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/d893beb50987c94bbfa80eb531aef18aa5499ef1920f2a5be0978e4c93af93c7.jpg)



时间 (s)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/b63918268b7318be34d2c374de1599c5aa2a7278e8f8e608b2c05ff9642c4d58.jpg)



时间 (s)



图 10 1、5、10 s 来流加速时间下 20N 期望升力的三种控制方法的动态响应.(a)–(c) 分别为 1、5、10 s 加速时间下的实测升力变化曲线与跟踪误差.



Fig. 10 Dynamic response of the three control methods under 20 N desired thrust with the 1, 5, and 10 s freestream-acceleration conditions. (a)–(c) show the measured thrust and tracking error under the 1, 5, and 10 s acceleration times, respectively.



表 4 统一扰动窗口下 9 种期望升力–加速时间组合的归一化 RMSE 及降幅



Table 4 Normalized RMSE and reduction ratios for the 9 desired-thrust/acceleration-time combinations using a common disturbance-window definition


<table><tr><td><eq>T_c/N</eq></td><td><eq>t_{ramp}/s</eq></td><td>Static/%</td><td>FB/%</td><td>FF+FB/%</td><td>FB 降幅/%</td><td>FF+FB 降幅/%</td></tr><tr><td>15</td><td>1</td><td>54.13</td><td>10.39</td><td>5.64</td><td>80.8</td><td>45.7</td></tr><tr><td>15</td><td>5</td><td>44.62</td><td>4.61</td><td>2.42</td><td>89.7</td><td>47.5</td></tr><tr><td>15</td><td>10</td><td>39.43</td><td>3.02</td><td>1.27</td><td>92.3</td><td>57.8</td></tr><tr><td>20</td><td>1</td><td>45.75</td><td>9.06</td><td>3.87</td><td>80.2</td><td>57.3</td></tr><tr><td>20</td><td>5</td><td>37.58</td><td>3.99</td><td>1.44</td><td>89.4</td><td>63.9</td></tr><tr><td>20</td><td>10</td><td>33.82</td><td>2.65</td><td>0.76</td><td>92.2</td><td>71.4</td></tr><tr><td>25</td><td>1</td><td>42.65</td><td>7.67</td><td>2.90</td><td>82.0</td><td>62.2</td></tr><tr><td>25</td><td>5</td><td>35.91</td><td>3.54</td><td>1.21</td><td>90.1</td><td>65.8</td></tr><tr><td>25</td><td>10</td><td>32.73</td><td>2.32</td><td>0.60</td><td>92.9</td><td>74.3</td></tr></table>

图 10 给出 20 N 期望升力下 1、5、10 s 三种来流加速时间的动态响应过程. 三种加速时间下固定控制量方案的失效程度相近, 升力跌落 6–9 N 且加速结束后长期无法恢复, 表明其偏差主要源于来流终值变化导致的静态标定失配, 而非来流变化速率;纯反馈方案的跟踪误差随加速变慢而单调下降, 且误差峰值均出现在加速刚结束附近, 反映其存在明显的滞后特性; 模型前馈与反馈复合控制在三种加速时间下均优于纯反馈, 且跟踪偏差始终为小幅负值 (轻微超调), 表明前馈项能够在来流刚开始变化时即同步提高控制量.

表 4 给出全部 9 个期望升力–加速时间组合在统一窗口规则下重新统计的归一化 RMSE, 所有工况均满足 $E _ { \mathrm { F F + F B } } < E _ { \mathrm { F B } } < E _ { \mathrm { s t a t i c } }$ . 相对于固定控制量, 纯反馈的 NRMSE 降低 80.2%–92.9%; 在纯反馈基础上加入旋翼升力逆模型前馈后,NRMSE 进一步降低 45.7%–74.3%, 复合控制的 NRMSE 为 0.60%–5.64%. 这些结果支持复合控制在所测轴向来流工况下均能降低升力跟踪误差. 尽管窗口规则已统一, 不同加速时间的窗口总长度及加速段与恢复段的权重仍有差异, 上述降幅仅作为当前试验条件下的描述性结果, 不据此推断前馈增益随加速时间增加的普遍规律.

![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/967ba5810ade192b6ded43f6aacf752850618f6e19cd6eae8d92dba130adf6ea.jpg)



图 11 三种控制方法归一化绝对误差随来流速度的变化



Fig. 11 Normalized absolute tracking error of the three control methods over the freestream-speed sweep


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/bb631b67bdd5475d3845658f01ac5d6eff02b208f3648ac33694bbd535eb73a6.jpg)


![image](https://cdn-mineru.openxlab.org.cn/result/2026-10-13/e823c6bf-ba17-4531-a287-10400734326a/fe7966e1fee0c53f90f01353f6c5a4e8ff8a4d0697bc601b018ea8c142e7facc.jpg)



图 12 模型前馈作用机理:(a) 前馈期望转速、复合控制与纯反馈的实测转速及各自来流速度;(b) 复合控制的前馈、反馈及总控制输出



Fig. 12 Feedforward mechanism: (a) feedforward rotor-speed command, measured rotor speeds and respective inflow speeds under combined control and feedback alone; (b) feedforward, feedback, and total outputs of combined control


图 11 给出三种控制方法归一化绝对误差随来流速度的变化, 对 15、20、25 N 期望升力与 1、5、10 s 加速时间共 9 个工况按来流速度统一叠加, 中线和阴影分别表示跨工况中位数和四分位区间. 这一处理旨在检验前述基于个别工况得到的结论是否对期望升力和加速快慢具有普适性, 而非仅在特定工况下成立. 结果显示, 固定控制量的误差随来流速度增大而单调上升, 且跨工况分散范围最宽; 纯反馈方案的误差同样随来流速度增大而扩大, 分散范围有所收窄; 模型前馈与反馈复合控制的误差曲线几乎不随来流速度变化, 且跨工况分散范围全程最窄.这表明模型前馈与反馈复合控制在整个来流速度范围内均具有最小且最稳定的误差水平, 该优势不依赖于具体的期望升力或加速时间设定, 验证了该控制方法的鲁棒性.

图 12 进一步分析复合控制的作用机理. 图 (a)对比 20 N/1 s 加速工况下复合控制与纯反馈的实测转速及各自来流速度, 并给出复合控制的前馈期望转速. 两次试验均以各自来流达到 10% 幅值的时刻对齐. 在给定期望升力与桨盘攻角下, 前馈期望转速由当前来流速度经静态非线性逆映射查表得到; 输入速度与输出转速各自达到 50% 幅值的时刻不同,不能据此认定前馈通道存在相位滞后或计算延迟.因此, 本节以两种方法的实测转速响应及升力误差作为控制效果的对照依据.

以 $- 2 \leq \tau \leq - 0 . 5 \mathrm { ~ s ~ }$ 与 $[ t _ { 9 0 } + 2 \mathrm { s } , t _ { 9 0 } + 3 \mathrm { s } ]$ 内的中位值分别确定各信号的低、高平台, 复合控制与纯反馈的实测转速达到 50% 增量的时刻分别约为 $\tau = 0 . 3 0 0$ 和 0.410 s, 复合控制较纯反馈提前约0.11 s; 两次试验的来流达到 50% 幅值的时刻分别约为 0.312 和 0.315 s. 在 20% 和 80% 增量处, 复合控制的实测转速也均较纯反馈更早到达. 上述指标描述该代表工况的幅值事件时序, 不作为系统纯延迟的估计. 结合图 (b) 可见, 前馈项依据来流变化直接提高控制输出, 反馈项进一步修正升力误差, 使转速补偿较早建立; 纯反馈则需根据已形成的升力偏差调整控制量. 相同 PID 参数下, 该工况的升力NRMSE 由纯反馈的 9.06% 降至复合控制的 3.87%,降低 57.3%. 转速响应对照与升力误差结果共同支持前馈对轴向来流扰动的补偿作用.

## 5 结论

本文针对多旋翼无人机机动飞行中的推进系统升力失配问题, 建立了从整机运动状态到单旋翼轴向升力的机理模型, 并提出基于模型前馈与直接力反馈的升力闭环控制方法. 模型未使用升力试验数据拟合气动参数或修正升力预测值, 但仍依赖桨叶几何获取与标定、XFOIL 数值极线以及转速–控制量静态标定. 在已测试的模型验证包线内, 总体归一化 RMSE 为 5.76%, 在 15<sup>◦</sup>–75<sup>◦</sup> 斜来流范围内, 按攻角汇总的归一化 RMSE 为 2.46%–5.02%.

控制效果的验证层级为执行器层单旋翼, 适用范围限定为本文所测 $\alpha _ { p } = 0 ^ { \circ }$ 的轴向强来流工况.在 15、20、25 N 期望升力与 1、5、10 s 加速时间构成的 9 个工况中, 按统一扰动窗口及期望升力归一化, 纯反馈相对固定控制量的 RMSE 降低 80.2%–92.9%, 前馈与反馈复合控制相对纯反馈进一步降低 45.7%–74.3%, 其 NRMSE 为 0.60%–5.64%. 在20 N/1 s 代表工况中, 复合控制实测转速达到 50%增量的时刻较纯反馈提前约 0.11 s, 与该工况升力NRMSE 降低 57.3% 的结果共同体现了前馈的扰动补偿作用. 上述结果量化了模型前馈在轴向强来流下对单旋翼升力跟踪的改善, 尚不能直接外推为斜来流控制效果或整机姿态、轨迹控制的端到端收益.

未来工作包括:1) 轻量化旋翼测量单元, 使其能够集成到多旋翼无人机结构中;2) 补充不同斜来流攻角下的闭环扰动试验, 检验前馈通道对来流方向变化的补偿能力;3) 在旋翼悬臂式旋转测试台末端安装可进行姿态控制的双旋翼单元或四旋翼整机,并结合整机飞行试验, 验证姿态、轨迹跟踪及控制分配的端到端收益.

## References



1 王姣娥, 杜德林, 陈卓, 黄洁, 张兵, 莫辉辉, 等. 中国低空经济发展指数报告 (2026). 北京: 中国科学院地理科学与资源研究所, 2026





2 Chen Lin, Miao Zhi-Qiang, Wang Xiang-Ke, Chen Mou, DuanHai-Bin, Wang Yao-Nan. Overview on autonomous aircrafttechnology and its application to low-altitude economy. Robot,2025, 47(3): 470−496(陈林, 缪志强, 王祥科, 陈谋, 段海滨, 王耀南. 自主飞行器技术及其在低空经济中的应用综述. 机器人, 2025, 47(3): 470−496)





3 Bauersfeld L, Kaufmann E, Foehn P, Sun S, Scaramuzza D. NeuroBEM: Hybrid aerodynamic quadrotor model. In: Proceedings of Robotics: Science and Systems XVII (RSS). Virtual: RSS Foundation, 2021 





4 Liu H, Lin D, Ye J, Jiang T, Huang J S. Quadrotor aggressive control based on angular acceleration feedback and high-fidelity propulsion model. IEEE Transactions on Industrial Electronics, DOI: 10.1109/TIE.2025.3572921 





5 Gonzalez-Morgado A, Sanchez-Cuevas P J, Heredia G, Ollero A. Rotor-force controller for multirotors under aerodynamic interferences. Aerospace Science and Technology, 2025, 157: 109861 





6 Jiang Han, Chang Yan-Chun, Yang Li-Ying, He Yu-Qing.Thrust feedback-based control method for rotor UAV. Robot,2026, 48(3): 518−530(蒋涵, 常彦春, 杨丽英, 何玉庆. 基于升力反馈的旋翼无人机控制方法. 机器人, 2026, 48(3): 518−530)





7 Jiang Han, Chen Ze-Hao, Chang Yan-Chun, Yang Li-Ying,Liu Lian-Qing, He Yu-Qing. A wind disturbance suppressionmethod for multirotor UAVs based on direct thrust control.SCIENTIA SINICA Technologica, 2026, 56, DOI: 10.1360/SST-2025-0274(蒋涵, 陈泽昊, 常彦春, 杨丽英, 刘连庆, 何玉庆. 基于直接升力控制的旋翼无人机风扰抑制方法. 中国科学: 技术科学, 2026, 56, DOI:10.1360/SST-2025-0274)





8 Theys B, Dimitriadis G, Hendrick P, De Schutter J. Experimental and numerical study of micro-aerial-vehicle propeller performance in oblique flow. Journal of Aircraft, 2017, 54(3): 1076−1084 





9 Serrano D, Ren M, Qureshi A J, Ghaemi S. Efect of disk angle-of-attack on aerodynamic performance of small propellers. Aerospace Science and Technology, 2019, 92: 901−914 





10 Simmons B M. System identification for propellers at high incidence angles. Journal of Aircraft, 2021, 58(6): 1336−1350 





11 Glauert H. A general theory of the autogyro. R&M No. 1111. London: British Aeronautical Research Committee, 1926 





12 Drela M. XFOIL: An analysis and design system for low Reynolds number airfoils. In: Low Reynolds Number Aerodynamics. Berlin: Springer, 1989. 1−12 





13 Meier L, Honegger D, Pollefeys M. PX4: A node-based multithreaded open source robotics framework for deeply embedded platforms. In: Proceedings of 2015 IEEE International Conference on Robotics and Automation (ICRA). Seattle, WA, USA: IEEE, 2015. 6235−6240 





14 Selig M S. UIUC airfoil data site. Urbana-Champaign: University of Illinois at Urbana-Champaign. https://m-selig.ae.illinois. edu/ads.html 





15 Tang E, Chung S J. Rapid extraction of propeller geometry using photogrammetry. International Journal of Micro Air Vehicles, 2022, 14: 1−22. DOI: 10.1177/17568293221132044 





16 Baltsavias E P. A comparison between photogrammetry and laser scanning. ISPRS Journal of Photogrammetry and Remote Sensing, 1999, 54(2−3): 83−94. DOI: 10.1016/S0924- 2716(99)00014-3 





17 Cheng Z, Li H, Asano Y, Zheng Y, Sato I. Multi-view 3D recon struction of a texture-less smooth surface of unknown generic reflectance. In: Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR). Virtual: IEEE, 2021. 16226−16235 





18 Carroll T B. A design methodology for rotors of small multirotor vehicles [Master thesis]. Toronto, Canada: Ryerson University, 2017 





19 Tal E, Karaman S. Accurate tracking of aggressive quadrotor trajectories using incremental nonlinear dynamic inversion and diferential flatness. IEEE Transactions on Control Systems Technology, 2021, 29(3): 1203−1218 





20 Wang M, Wang Q, Wang Z, Gao Y, Wang J, Cui C, et al. Unlocking aerobatic potential of quadcopters: Autonomous freestyle flight generation and execution. Science Robotics, 2025, 10: eadp9905 



【待填写作者姓名】 【待填写作者简介】.

E-mail: 【待填写邮箱】

(【待填写英文作者姓名】 【待填写英文作者简介】.)