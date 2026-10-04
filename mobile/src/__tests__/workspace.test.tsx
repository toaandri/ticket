import { beforeEach, expect, jest, test } from '@jest/globals';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import Index from '../../app/index';
import { getRefresh, request, saveRefresh } from '../api';

jest.mock('../api', () => ({ getRefresh: jest.fn(), request: jest.fn(), saveRefresh: jest.fn() }));
jest.mock('react-native-safe-area-context', () => ({ SafeAreaView: jest.requireActual<typeof import('react-native')>('react-native').View }));
const getRefreshMock = jest.mocked(getRefresh);
const requestMock = jest.mocked(request);
const saveRefreshMock = jest.mocked(saveRefresh);

beforeEach(() => {
  jest.clearAllMocks();
  getRefreshMock.mockResolvedValue(null);
  saveRefreshMock.mockResolvedValue(undefined);
});

test('signs in and stores the refresh token securely through the session adapter', async () => {
  requestMock.mockResolvedValueOnce({ access: 'access', refresh: 'refresh' })
    .mockResolvedValueOnce({ id: 'user-1', email: 'alice@example.com', display_name: 'Alice' })
    .mockResolvedValueOnce({ results: [{ id: 'org-1', name: 'Concert team', slug: 'concert-team' }] });
  const screen = render(<Index />);
  await waitFor(() => expect(screen.queryByLabelText('Loading workspace')).toBeNull());
  fireEvent.changeText(screen.getByLabelText('Email'), 'alice@example.com');
  fireEvent.changeText(screen.getByLabelText('Password'), 'example-password-93!');
  fireEvent.press(screen.getByText('Sign in'));
  await waitFor(() => expect(screen.getByText('Concert team')).toBeTruthy());
  expect(saveRefreshMock).toHaveBeenCalledWith('refresh');
  expect(screen.getByText('Hello, Alice.')).toBeTruthy();
});

test('shows API failure without opening an authenticated workspace', async () => {
  requestMock.mockRejectedValueOnce(new Error('Invalid credentials.'));
  const screen = render(<Index />);
  await waitFor(() => expect(screen.queryByLabelText('Loading workspace')).toBeNull());
  fireEvent.changeText(screen.getByLabelText('Email'), 'alice@example.com');
  fireEvent.changeText(screen.getByLabelText('Password'), 'wrong');
  fireEvent.press(screen.getByText('Sign in'));
  await waitFor(() => expect(screen.getByText('Invalid credentials.')).toBeTruthy());
  expect(screen.queryByText('Your organizations')).toBeNull();
  expect(saveRefreshMock).not.toHaveBeenCalled();
});
