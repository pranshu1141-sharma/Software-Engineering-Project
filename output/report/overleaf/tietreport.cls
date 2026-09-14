%% TIET report class, transcribed from the user-supplied Overleaf template.
%% Source: https://www.overleaf.com/read/rjgcdqyqkxnd#0c5313
%% Original class v1.0.4 (2026/09/03); explanatory comments abbreviated.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{tietreport}[2026/09/03 TIET Report Class v1.0.4]
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{report}}
\ProcessOptions\relax
\LoadClass[twoside,12pt,openright]{report}
\RequirePackage[inner=1.5in,outer=1in,top=1.8in,bottom=0.85in]{geometry}
\RequirePackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE]{\thepage \quad \@tpHeader}
\fancyhead[RO]{\@tpTitle \quad \thepage}
\renewcommand{\headrulewidth}{0.5pt}
\renewcommand{\footrulewidth}{0pt}
\RequirePackage{titlesec}
\titleformat{\chapter}[display]{\raggedleft\bfseries\large}{Chapter \thechapter}{0.3em}{\huge}[\vspace{0.1em}\hrule]
\titlespacing*{\chapter}{0pt}{-50pt}{40pt}
\assignpagestyle{\chapter}{empty}
\RequirePackage{hyperref}
\RequirePackage{graphicx}
\RequirePackage{amsmath}
\RequirePackage{amssymb}
\newcommand{\@tpHeader}{UCS 503 Software Engineering Project Report}
\newcommand{\@tpTitle}{Proposal to Final}
\newcommand{\@tpSubTitle}{How to Write a Project Report}
\newcommand{\@tpAuthors}{Student names}
\newcommand{\@tpSubText}{Group and programme}
\newcommand{\@tpAdvisor}{Advisor name}
\newcommand{\@tpFooter}{Computer Science and Engineering Department\\Thapar Institute of Engineering and Technology, Patiala}
\newcommand{\TitlePageHeader}[1]{\renewcommand{\@tpHeader}{#1}}
\newcommand{\ProjectTitle}[1]{\renewcommand{\@tpTitle}{#1}}
\newcommand{\ProjectSubTitle}[1]{\renewcommand{\@tpSubTitle}{#1}}
\renewcommand{\author}[1]{\renewcommand{\@tpAuthors}{#1}}
\newcommand{\TitlePageSubText}[1]{\renewcommand{\@tpSubText}{#1}}
\newcommand{\AdvisorName}[1]{\renewcommand{\@tpAdvisor}{#1}}
\newcommand{\TitlePageFooterText}[1]{\renewcommand{\@tpFooter}{#1}}
\renewcommand{\maketitle}{%
\begin{titlepage}\thispagestyle{empty}\centering
\vspace*{0.5cm}
{\large\textbf{\@tpHeader}}
\vspace{2cm}\par
{\LARGE\textbf{\@tpTitle}}
\vspace{0.2cm}\par
{\@tpSubTitle}
\vspace{3.5cm}\par
{\large\textbf{Submitted by:}}
\vspace{0.2cm}\par
{\large\@tpAuthors}
\vspace{0.5cm}\par
{\normalsize\@tpSubText}
\vfill
{\large\textbf{Submitted to:}}
\vspace{0.2cm}\par
{\normalsize\@tpAdvisor}
\vspace{2cm}\par
{\normalsize\@tpFooter}
\end{titlepage}
\newpage\thispagestyle{empty}}
\endinput
