/* ===========================================
   ATLAS OS - STYLE V1.1
=========================================== */

*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

html{
    scroll-behavior:smooth;
}

body{

    font-family:'Inter',sans-serif;

    background:#050816;

    color:#F8FAFC;

    overflow-x:hidden;

}

/* ===========================================
   SPLASH SCREEN
=========================================== */

#splash{

    position:fixed;

    inset:0;

    background:linear-gradient(180deg,#081120,#050816);

    display:flex;

    justify-content:center;

    align-items:center;

    z-index:9999;

    animation:fadeSplash 1s ease 3.5s forwards;

}

.logo-container{

    text-align:center;

    animation:logoIntro 1.2s ease;

}

/* ===========================================
   LOGO
=========================================== */

.logo-circle{

    width:120px;

    height:120px;

    margin:auto;

    border-radius:50%;

    display:flex;

    justify-content:center;

    align-items:center;

    background:linear-gradient(
        135deg,
        #38BDF8,
        #2563EB
    );

    color:white;

    font-size:54px;

    font-weight:700;

    box-shadow:

    0 0 25px rgba(56,189,248,.55),

    0 0 70px rgba(56,189,248,.35);

    animation:pulse 3s infinite;

}

.logo-container h1{

    margin-top:25px;

    font-size:42px;

    font-weight:700;

}

.logo-container p{

    margin-top:18px;

    color:#94A3B8;

    line-height:1.6;

}

/* ===========================================
   HEADER
=========================================== */

header{

    display:flex;

    justify-content:space-between;

    align-items:center;

    padding:30px 24px;

}

header small{

    color:#64748B;

}

header h2{

    margin-top:5px;

    font-size:30px;

}

.avatar{

    font-size:46px;

    color:#38BDF8;

}

/* ===========================================
   HERO
=========================================== */

.hero-card{

    margin:25px;

    padding:35px;

    border-radius:30px;

    background:rgba(17,24,39,.75);

    backdrop-filter:blur(20px);

    border:1px solid rgba(255,255,255,.06);

    box-shadow:

    0 20px 50px rgba(0,0,0,.40);

}

.hero-card h1{

    font-size:36px;

    line-height:1.3;

}

.hero-card p{

    margin-top:20px;

    color:#CBD5E1;

    font-size:18px;

}

.hero-card button{

    margin-top:35px;

    width:100%;

    padding:18px;

    border:none;

    border-radius:18px;

    background:linear-gradient(
        135deg,
        #38BDF8,
        #2563EB
    );

    color:white;

    font-size:17px;

    cursor:pointer;

    transition:.35s;

}

.hero-card button:hover{

    transform:translateY(-4px);

    box-shadow:

    0 20px 40px rgba(37,99,235,.45);

}

/* ===========================================
   CARDS
=========================================== */

.cards{

    display:grid;

    grid-template-columns:repeat(2,1fr);

    gap:18px;

    padding:25px;

}

.card{

    background:#111827;

    border-radius:24px;

    padding:22px;

    border:1px solid rgba(255,255,255,.05);

    transition:.35s;

}

.card:hover{

    transform:translateY(-6px);

}

.card h3{

    color:#94A3B8;

    font-size:15px;

}

.card span{

    display:block;

    margin-top:18px;

    font-size:34px;

    font-weight:700;

}

/* ===========================================
   NAVIGATION
=========================================== */

nav{

    position:fixed;

    bottom:0;

    width:100%;

    display:flex;

    justify-content:space-around;

    padding:14px 0;

    background:rgba(10,15,30,.90);

    backdrop-filter:blur(18px);

    border-top:1px solid rgba(255,255,255,.05);

}

nav button{

    background:none;

    border:none;

    color:#94A3B8;

    cursor:pointer;

    display:flex;

    flex-direction:column;

    align-items:center;

    font-size:12px;

    transition:.3s;

}

nav button span{

    font-size:26px;

    margin-bottom:5px;

}

nav button:hover{

    color:#38BDF8;

}

/* ===========================================
   ANIMATIONS
=========================================== */

@keyframes logoIntro{

    from{

        transform:translateY(30px) scale(.8);

        opacity:0;

    }

    to{

        transform:translateY(0) scale(1);

        opacity:1;

    }

}

@keyframes pulse{

    0%{

        transform:scale(1);

    }

    50%{

        transform:scale(1.08);

    }

    100%{

        transform:scale(1);

    }

}

@keyframes fadeSplash{

    to{

        opacity:0;

        visibility:hidden;

    }

}

/* ===========================================
   RESPONSIVE
=========================================== */

@media(min-width:900px){

.cards{

grid-template-columns:repeat(4,1fr);

}

.hero-card{

max-width:900px;

margin:40px auto;

}

header{

max-width:1200px;

margin:auto;

}

}
