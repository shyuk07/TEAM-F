import { Link } from 'react-router';
import { useAuth } from '@/features/auth';
import {
  LocationChip,
  LocationSheet,
  NearbyOfferSection,
  OfferSearchForm,
  SortChips,
  useHomeOffers,
  useLocationSheet,
} from '@/features/offers';
import { ROUTES } from '@/shared/lib/routes';

export function HomePage() {
  const home = useHomeOffers();
  const sheet = useLocationSheet(home);
  const { state } = useAuth();
  return (
    <>
      <div className="bar">
        <span className="logo">마감직전</span>
        <LocationChip label={home.chipLabel} open={sheet.isOpen} onClick={sheet.open} />
        <span className="sp"></span>
        {state.status === 'anonymous' ? <Link to={ROUTES.login}>로그인</Link> : null}
      </div>
      <div className="body">
        <OfferSearchForm keyword={home.keyword} onSubmit={home.submitKeyword} />
        <SortChips sort={home.sort} hasLocation={home.hasLocation} onSelect={home.selectSort} />
        <NearbyOfferSection home={home} />
      </div>
      <Link className="link" to={ROUTES.ownerSignup}>
        사장님이신가요? 입점 신청
      </Link>
      {sheet.isOpen ? <LocationSheet sheet={sheet} /> : null}
    </>
  );
}
